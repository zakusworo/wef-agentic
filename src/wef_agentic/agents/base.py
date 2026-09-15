"""Base Agent class — provider-agnostic interpretation of deterministic nexus results."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from wef_agentic.config.settings import load_llm_config
from wef_agentic.llm.footprint import FootprintEntry
from wef_agentic.llm.provider import LLMProvider, get_provider_for_agent
from wef_agentic.llm.types import EmptyCompletionError, LLMResponse, Message, Usage

if TYPE_CHECKING:
    from wef_agentic.orchestration.nexus import NexusState

BOUNDED_AUTONOMY_NOTE = (
    "PENTING (WEF 2026a bounded autonomy): Output Anda adalah ADVISORY ONLY. "
    "Anda menarget function di area low-readiness (#43 Policy forecasting / "
    "#55 Policy impact prediction). Semua rekomendasi wajib di-review oleh "
    "analis manusia sebelum digunakan untuk decision-making. Sertakan caveat "
    "eksplisit di akhir output Anda."
)

NUMBERS_ARE_GIVEN_NOTE = (
    "Semua angka di bawah dihitung deterministik oleh framework. Jangan menghitung "
    "ulang, mengubah, atau mengarang angka; kutip angka apa adanya."
)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass
class AgentOutput:
    agent: str
    content: str
    tool_outputs: list[dict] = field(default_factory=list)
    usage_input_tokens: int = 0
    usage_output_tokens: int = 0
    provider: str = ""
    model: str = ""
    meta: dict[str, Any] = field(default_factory=dict)


class Agent:
    """Base class — subclass overrides system_prompt + run()."""

    name: str = "base"
    system_prompt: str = "You are a generic agent."

    def __init__(self, provider: LLMProvider | None = None):
        self.provider = provider or get_provider_for_agent(self.name)

    async def _call_llm(self, user_prompt: str) -> LLMResponse:
        """Call the provider; retry once on an empty answer, raise if still empty.

        Reasoning models can spend the whole budget on thinking and return no text.
        Passing that on silently would let downstream agents synthesize from nothing.
        Usage of every attempt is summed so the footprint counts wasted tokens too.
        """
        system = self.system_prompt + "\n\n" + BOUNDED_AUTONOMY_NOTE
        messages = [
            Message(role="system", content=system),
            Message(role="user", content=user_prompt),
        ]
        requested_model = self.provider.model
        attempts = [await self.provider.chat(messages)]

        if not attempts[-1].content.strip():
            cap = (load_llm_config().get("retry") or {}).get("max_tokens_cap", 16000)
            original = self.provider.max_tokens
            if attempts[-1].truncated:
                self.provider.max_tokens = max(original, min(original * 2, cap))
            try:
                attempts.append(await self.provider.chat(messages))
            finally:
                self.provider.max_tokens = original

        response = attempts[-1]
        if not response.content.strip():
            raise EmptyCompletionError(
                f"{self.name}: empty completion from {response.provider}/{response.model} "
                f"after {len(attempts)} attempts (done_reason={response.done_reason}, "
                f"thinking={len(response.thinking)} chars). Raise max_tokens for this agent "
                "in config/llm.yaml or use a non-reasoning model."
            )

        response.usage = Usage(
            input_tokens=sum(a.usage.input_tokens for a in attempts),
            output_tokens=sum(a.usage.output_tokens for a in attempts),
        )
        response.meta = {
            **response.meta,
            "requested_model": requested_model,
            "attempts": len(attempts),
            "done_reason": response.done_reason,
            "truncated": response.truncated,
            "thinking_chars": len(response.thinking),
            "system_prompt_sha256": _sha256(system),
            "prompt_sha256": _sha256(user_prompt),
        }
        return response

    def _output(self, response: LLMResponse, tool_outputs: list[dict] | None = None) -> AgentOutput:
        return AgentOutput(
            agent=self.name,
            content=response.content,
            tool_outputs=tool_outputs or [],
            usage_input_tokens=response.usage.input_tokens,
            usage_output_tokens=response.usage.output_tokens,
            provider=response.provider,
            model=response.model,
            meta=response.meta,
        )

    @staticmethod
    def _format_tool_outputs(tool_outputs: list[dict]) -> str:
        """Format tool outputs ke prompt-friendly text."""
        lines = []
        for i, t in enumerate(tool_outputs, 1):
            name = t.get("tool", f"tool_{i}")
            data = t.get("data", {})
            lines.append(f"### Tool #{i}: {name}\n```json\n{json.dumps(data, indent=2, default=str)}\n```")
        return "\n\n".join(lines)

    @staticmethod
    def _scenario_header(scenario: dict[str, Any], nexus: NexusState) -> str:
        ctx = nexus.location_context
        loc = nexus.location
        lines = [
            f"Skenario: {scenario.get('name', 'UNNAMED')}",
            f"Lokasi: {ctx['display']}",
            "Data lokal: " + ("ya (BPS)" if ctx["has_local_data"]
                              else "tidak — sebagian besar input adalah proxy tingkat negara"),
            f"Koordinat: lat={loc['lat']:.3f}, lon={loc['lon']:.3f}",
            f"Horizon: {scenario.get('horizon', 2050)}",
        ]
        if ctx.get("fires"):
            lines.append("Isu kunci lokasi: " + "; ".join(ctx["fires"]))
        if ctx.get("sub_das"):
            lines.append("Sub-DAS: " + ", ".join(ctx["sub_das"]))
        return "\n".join(lines)

    async def run(self, scenario: dict[str, Any], nexus: NexusState) -> AgentOutput:
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
