"""Base Agent class — provider-agnostic, scripted-tool-dispatch friendly."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from wef_agentic.llm.footprint import FootprintEntry
from wef_agentic.llm.provider import LLMProvider, get_provider_for_agent
from wef_agentic.llm.types import LLMResponse, Message

BOUNDED_AUTONOMY_NOTE = (
    "PENTING (WEF 2026a bounded autonomy): Output Anda adalah ADVISORY ONLY. "
    "Anda menarget function di area low-readiness (#43 Policy forecasting / "
    "#55 Policy impact prediction). Semua rekomendasi wajib di-review oleh "
    "analis manusia sebelum digunakan untuk decision-making. Sertakan caveat "
    "eksplisit di akhir output Anda."
)


@dataclass
class AgentOutput:
    agent: str
    content: str
    tool_outputs: list[dict] = field(default_factory=list)
    usage_input_tokens: int = 0
    usage_output_tokens: int = 0
    provider: str = ""
    model: str = ""


class Agent:
    """Base class — subclass overrides system_prompt + run()."""

    name: str = "base"
    system_prompt: str = "You are a generic agent."

    def __init__(self, provider: LLMProvider | None = None):
        self.provider = provider or get_provider_for_agent(self.name)

    async def _call_llm(self, user_prompt: str) -> LLMResponse:
        messages = [
            Message(role="system", content=self.system_prompt + "\n\n" + BOUNDED_AUTONOMY_NOTE),
            Message(role="user", content=user_prompt),
        ]
        return await self.provider.chat(messages)

    def _format_tool_outputs(self, tool_outputs: list[dict]) -> str:
        """Format tool outputs ke prompt-friendly text."""
        lines = []
        for i, t in enumerate(tool_outputs, 1):
            name = t.get("tool", f"tool_{i}")
            data = t.get("data", {})
            lines.append(f"### Tool #{i}: {name}\n```json\n{json.dumps(data, indent=2, default=str)}\n```")
        return "\n\n".join(lines)

    async def run(self, scenario: dict[str, Any]) -> AgentOutput:
        """Override in subclass."""
        raise NotImplementedError

    def to_footprint(self, output: AgentOutput) -> FootprintEntry:
        return FootprintEntry(
            agent=self.name,
            provider=output.provider,
            model=output.model,
            input_tokens=output.usage_input_tokens,
            output_tokens=output.usage_output_tokens,
        )
