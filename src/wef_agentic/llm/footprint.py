"""Nexus footprint tracker — operasionalisasi WEF (2026b) untuk LLM usage.

Proxies bukan measurement; honest caveats in paper.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from wef_agentic.config.settings import load_llm_config


@dataclass
class FootprintEntry:
    agent: str
    provider: str
    model: str
    input_tokens: int
    output_tokens: int

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass
class NexusFootprint:
    entries: list[FootprintEntry] = field(default_factory=list)

    def add(self, entry: FootprintEntry) -> None:
        self.entries.append(entry)

    @property
    def total_tokens(self) -> int:
        return sum(e.total_tokens for e in self.entries)

    def estimate(self) -> dict[str, float]:
        """Compute proxy estimates per WEF 2026b benchmarks."""
        cfg = load_llm_config().get("footprint", {})
        kwh_per_1k = cfg.get("kwh_per_1k_tokens", 0.0003)
        water_per_1k = cfg.get("water_l_per_1k_tokens", 0.005)
        co2_per_kwh = cfg.get("co2_kg_per_kwh", 0.4)

        kwh = self.total_tokens / 1000 * kwh_per_1k
        water_l = self.total_tokens / 1000 * water_per_1k
        co2_kg = kwh * co2_per_kwh

        return {
            "total_tokens": self.total_tokens,
            "energy_kwh": kwh,
            "water_l": water_l,
            "co2_kg": co2_kg,
        }

    def by_agent(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for e in self.entries:
            out[e.agent] = out.get(e.agent, 0) + e.total_tokens
        return out
