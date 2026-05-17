"""Claude Agent SDK provider — pakai Claude Code subscription via claude-agent-sdk."""
from __future__ import annotations

from typing import Any

from wef_agentic.llm.provider import LLMProvider
from wef_agentic.llm.types import LLMResponse, Message, ToolSchema, Usage


class ClaudeAgentSDKProvider(LLMProvider):
    """Wraps claude-agent-sdk untuk mengakses Claude via Claude Code subscription.

    Tidak butuh ANTHROPIC_API_KEY — uses subscription billing.
    Untuk MVP, kita pakai query() one-shot (no session history).
    """

    name = "claude-agent-sdk"

    def __init__(self, model: str, max_tokens: int = 4096, temperature: float = 0.2):
        super().__init__(model=model, max_tokens=max_tokens, temperature=temperature)
        # Lazy import — SDK butuh Claude Code CLI installed
        try:
            from claude_agent_sdk import ClaudeAgentOptions, query  # type: ignore

            self._query = query
            self._ClaudeAgentOptions = ClaudeAgentOptions
        except ImportError as e:
            raise RuntimeError(
                "claude-agent-sdk tidak ter-install. Jalankan: pip install claude-agent-sdk"
            ) from e

    async def chat(
        self,
        messages: list[Message],
        tools: list[ToolSchema] | None = None,
    ) -> LLMResponse:
        # Compose system prompt + user prompt
        # Claude Agent SDK pattern: system_prompt + single prompt string
        system_parts: list[str] = []
        prompt_parts: list[str] = []

        for m in messages:
            if m.role == "system":
                system_parts.append(m.content)
            elif m.role == "user":
                prompt_parts.append(m.content)
            elif m.role == "assistant":
                # Untuk one-shot query, kita inline conversation history sebagai context
                prompt_parts.append(f"[Previous assistant turn]: {m.content}")

        system_prompt = "\n\n".join(system_parts) if system_parts else None
        prompt = "\n\n".join(prompt_parts) if prompt_parts else ""

        options_kwargs: dict[str, Any] = {}
        if system_prompt:
            options_kwargs["system_prompt"] = system_prompt
        # Untuk MVP kita batasi tools default Claude Code (Read, Write, Bash) supaya
        # tidak terjadi side-effects. Agen kita = reasoning only.
        options_kwargs["allowed_tools"] = []

        options = self._ClaudeAgentOptions(**options_kwargs)

        content_chunks: list[str] = []
        input_tokens = 0
        output_tokens = 0

        async for msg in self._query(prompt=prompt, options=options):
            # claude-agent-sdk streams berbagai message types
            # Kita ekstrak text content + usage
            msg_type = type(msg).__name__
            if msg_type == "AssistantMessage":
                for block in getattr(msg, "content", []) or []:
                    if hasattr(block, "text"):
                        content_chunks.append(block.text)
            elif msg_type == "ResultMessage":
                usage = getattr(msg, "usage", None) or {}
                if isinstance(usage, dict):
                    input_tokens = usage.get("input_tokens", 0)
                    output_tokens = usage.get("output_tokens", 0)

        return LLMResponse(
            content="".join(content_chunks),
            usage=Usage(input_tokens=input_tokens, output_tokens=output_tokens),
            provider=self.name,
            model=self.model,
            meta={},
        )
