"""Ollama provider — supports both local (localhost:11434) dan cloud (ollama.com)."""
from __future__ import annotations

import os

import httpx
from ollama import AsyncClient

from wef_agentic.config.settings import settings
from wef_agentic.llm.provider import LLMProvider
from wef_agentic.llm.types import LLMResponse, Message, ToolSchema, Usage


class OllamaProvider(LLMProvider):
    """Wraps ollama-python AsyncClient.

    Cloud vs local di-bedakan via flag `cloud`:
    - Local: hostnya settings.ollama_host (default localhost:11434)
    - Cloud: hostnya https://ollama.com, butuh API key
    """

    def __init__(
        self,
        model: str,
        max_tokens: int = 4096,
        temperature: float = 0.2,
        cloud: bool = False,
    ):
        super().__init__(model=model, max_tokens=max_tokens, temperature=temperature)
        self.cloud = cloud
        self.name = "ollama-cloud" if cloud else "ollama-local"

        if cloud:
            api_key = settings.ollama_api_key or os.getenv("OLLAMA_API_KEY", "")
            if not api_key:
                raise ValueError(
                    "OLLAMA_API_KEY tidak ditemukan untuk provider ollama-cloud. "
                    "Set di .env atau ganti provider ke ollama-local."
                )
            self.client = AsyncClient(
                host="https://ollama.com",
                headers={"Authorization": f"Bearer {api_key}"},
            )
        else:
            self.client = AsyncClient(host=settings.ollama_host)

    async def chat(
        self,
        messages: list[Message],
        tools: list[ToolSchema] | None = None,
    ) -> LLMResponse:
        ollama_messages = [{"role": m.role, "content": m.content} for m in messages]

        kwargs: dict = {
            "model": self.model,
            "messages": ollama_messages,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_tokens,
            },
        }
        if tools:
            kwargs["tools"] = [self._tool_to_ollama_format(t) for t in tools]

        try:
            response = await self.client.chat(**kwargs)
        except httpx.HTTPError as e:
            raise RuntimeError(f"Ollama call failed ({self.name}, {self.model}): {e}") from e

        content = response.get("message", {}).get("content", "")
        usage = Usage(
            input_tokens=response.get("prompt_eval_count", 0),
            output_tokens=response.get("eval_count", 0),
        )

        return LLMResponse(
            content=content,
            usage=usage,
            provider=self.name,
            model=self.model,
            meta={
                "total_duration_ns": response.get("total_duration", 0),
                "done_reason": response.get("done_reason"),
            },
        )

    @staticmethod
    def _tool_to_ollama_format(tool: ToolSchema) -> dict:
        return {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            },
        }
