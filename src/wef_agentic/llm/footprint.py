"""Nexus footprint tracker — operasionalisasi WEF (2026b) untuk LLM usage.

Method (all constants in config/llm.yaml → footprint:):

    IT energy (kWh)  = (output_tokens + w_in · input_tokens) / 1000
                       × kwh_per_1k_output_tokens × size_multiplier(model)
    Facility energy  = IT energy × PUE(provider)
    On-site water    = IT energy × WUE(provider)                  (cooling)
    Off-site water   = facility energy × EWIF(provider)           (electricity generation)
    CO₂eq            = facility energy × grid factor(provider)

Water accounting follows Li et al. (2023), arXiv:2304.03271. Every factor is a
proxy, not a measurement; unknown factors are reported as missing, not zero.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from wef_agentic.config.settings import load_llm_config

_DEFAULT_CFG = {
    "kwh_per_1k_output_tokens": 0.0003,
    "input_token_weight": 0.1,
    "size_multiplier": {"small": 0.1, "medium": 1.0, "large": 3.0},
    "size_patterns": [],
    "providers": {},
}


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


def _footprint_cfg() -> dict:
    return {**_DEFAULT_CFG, **(load_llm_config().get("footprint") or {})}


def model_size_class(model: str, cfg: dict | None = None) -> str:
    """First matching regex in `size_patterns` wins; default 'medium'."""
    cfg = cfg or _footprint_cfg()
    for rule in cfg.get("size_patterns") or []:
        if re.search(rule["pattern"], model or "", flags=re.IGNORECASE):
            return rule["size"]
    return "medium"


@dataclass
class NexusFootprint:
    entries: list[FootprintEntry] = field(default_factory=list)

    def add(self, entry: FootprintEntry) -> None:
        self.entries.append(entry)

    @property
    def total_tokens(self) -> int:
        return sum(e.total_tokens for e in self.entries)

    def estimate(self, cfg: dict | None = None) -> dict:
        """Compute proxy estimates per entry and in total."""
        cfg = cfg or _footprint_cfg()
        providers = cfg.get("providers") or {}
        w_in = cfg["input_token_weight"]

        per_entry = []
        missing_offsite = set()
        for e in self.entries:
            p = providers.get(e.provider) or providers.get("default") or {}
            size = model_size_class(e.model, cfg)
            weighted_k = (e.output_tokens + w_in * e.input_tokens) / 1000
            it_kwh = weighted_k * cfg["kwh_per_1k_output_tokens"] * cfg["size_multiplier"][size]
            facility_kwh = it_kwh * p.get("pue", 1.0)
            onsite_l = it_kwh * p.get("wue_onsite_l_per_kwh", 0.0)
            ewif = p.get("ewif_l_per_kwh")
            offsite_l = facility_kwh * ewif if ewif is not None else None
            if ewif is None:
                missing_offsite.add(e.provider)
            co2_factor = p.get("co2_kg_per_kwh")
            per_entry.append({
                "agent": e.agent,
                "provider": e.provider,
                "model": e.model,
                "size_class": size,
                "tokens": e.total_tokens,
                "energy_kwh": facility_kwh,
                "water_onsite_l": onsite_l,
                "water_offsite_l": offsite_l,
                "co2_kg": facility_kwh * co2_factor if co2_factor is not None else None,
            })

        energy = sum(r["energy_kwh"] for r in per_entry)
        onsite = sum(r["water_onsite_l"] for r in per_entry)
        offsite = sum(r["water_offsite_l"] or 0.0 for r in per_entry)
        co2 = sum(r["co2_kg"] or 0.0 for r in per_entry)

        notes = []
        if missing_offsite:
            notes.append(
                "Off-site (electricity-generation) water not estimated for: "
                + ", ".join(sorted(missing_offsite))
            )

        return {
            "total_tokens": self.total_tokens,
            "energy_kwh": energy,
            "water_l": onsite + offsite,
            "water_onsite_l": onsite,
            "water_offsite_l": offsite,
            "co2_kg": co2,
            "per_entry": per_entry,
            "notes": notes,
        }

    def by_agent(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for e in self.entries:
            out[e.agent] = out.get(e.agent, 0) + e.total_tokens
        return out
