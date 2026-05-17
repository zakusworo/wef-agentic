"""Abstract base + factory untuk LLM providers."""
from __future__ import annotations

import os
from abc import ABC, abstractmethod

from wef_agentic.config.settings import load_llm_config, settings
from wef_agentic.llm.types import LLMResponse, Message, ToolSchema


class LLMProvider(ABC):
    """Universal LLM provider interface."""

    name: str = "abstract"

    def __init__(self, model: str, max_tokens: int = 4096, temperature: float = 0.2):
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature

    @abstractmethod
    async def chat(
        self,
        messages: list[Message],
        tools: list[ToolSchema] | None = None,
    ) -> LLMResponse:
        ...

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} model={self.model}>"


# ──────────────────────────────────────────────────────────────────────────────
# Factory dengan layered provider/model resolution
# ──────────────────────────────────────────────────────────────────────────────


# Default models per provider (fallback jika yaml tidak punya field model_*)
DEFAULT_MODELS = {
    "ollama-local": "gemma4:e4b",
    "ollama-cloud": "deepseek-v4-pro:cloud",
    "claude-agent-sdk": "claude-sonnet-4-6",
}

# Model field name per provider di yaml
MODEL_FIELD_PER_PROVIDER = {
    "ollama-local": "model_local",
    "ollama-cloud": "model",                # default field (legacy)
    "claude-agent-sdk": "model_claude",
}


def _resolve_provider_name(merged_cfg: dict) -> str:
    """Resolve nama provider dengan priority:
    1. Runtime override (env WEF_AGENTIC_PROVIDER_OVERRIDE) — diset oleh UI saat ini
    2. yaml per-agent
    3. yaml defaults
    4. settings (.env default)
    """
    override = os.environ.get("WEF_AGENTIC_PROVIDER_OVERRIDE", "").strip()
    if override:
        return override
    return merged_cfg.get("provider") or settings.provider


def _resolve_model(provider_name: str, merged_cfg: dict) -> str:
    """Resolve model untuk provider. Priority:
    1. yaml field spesifik provider (model_local / model / model_claude)
    2. yaml field generic `model` (legacy)
    3. global env override (WEF_AGENTIC_MODEL_OVERRIDE)
    4. DEFAULT_MODELS table
    """
    model_override = os.environ.get("WEF_AGENTIC_MODEL_OVERRIDE", "").strip()
    if model_override:
        return model_override

    field = MODEL_FIELD_PER_PROVIDER.get(provider_name, "model")
    model = merged_cfg.get(field)
    if model:
        return model

    # Fallback ke field generic 'model' kalau spesifik tidak ada
    model = merged_cfg.get("model")
    if model:
        # Tapi cek dulu: model cloud (e.g. 'deepseek-v4-pro:cloud') tidak cocok untuk ollama-local
        if provider_name == "ollama-local" and (":cloud" in model or model.endswith("cloud")):
            return DEFAULT_MODELS["ollama-local"]
        return model

    return DEFAULT_MODELS.get(provider_name, "gemma4:e4b")


def get_provider_for_agent(agent_name: str) -> LLMProvider:
    """Resolve provider untuk agen tertentu dari config/llm.yaml + env override."""
    cfg = load_llm_config()
    defaults = cfg.get("defaults", {})
    agent_cfg = cfg.get("agents", {}).get(agent_name, {})
    merged = {**defaults, **agent_cfg}

    provider_name = _resolve_provider_name(merged)
    model = _resolve_model(provider_name, merged)
    max_tokens = merged.get("max_tokens", 4096)
    temperature = merged.get("temperature", 0.2)

    if provider_name == "ollama-local":
        from wef_agentic.llm.ollama_provider import OllamaProvider
        return OllamaProvider(model=model, max_tokens=max_tokens, temperature=temperature, cloud=False)

    if provider_name == "ollama-cloud":
        from wef_agentic.llm.ollama_provider import OllamaProvider
        return OllamaProvider(model=model, max_tokens=max_tokens, temperature=temperature, cloud=True)

    if provider_name == "claude-agent-sdk":
        from wef_agentic.llm.claude_agent_provider import ClaudeAgentSDKProvider
        return ClaudeAgentSDKProvider(model=model, max_tokens=max_tokens, temperature=temperature)

    raise ValueError(f"Unknown provider: {provider_name}")
