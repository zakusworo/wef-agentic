"""Replay a recorded Claude run with its matching synthetic nexus snapshot."""
from __future__ import annotations

import json

from wef_agentic.agents.base import AgentOutput
from wef_agentic.config.settings import ROOT
from wef_agentic.llm.footprint import FootprintEntry, NexusFootprint
from wef_agentic.orchestration.graph import ScenarioRunResult
from wef_agentic.orchestration.nexus import NexusState


def load_demo() -> ScenarioRunResult:
    runs = ROOT / "docs" / "runs"
    record = json.loads((runs / "run_S2_JETP_Aligned_sleman_claude-agent-sdk_20260920_143021.json").read_text())
    sweep = json.loads((runs / "sweep_synthetic_20260920.json").read_text())
    snapshot = next(row for row in sweep["results"] if row["id"] == "S2_JETP_Aligned")
    if snapshot["scenario"] != record["scenario"]:
        raise ValueError("Demo scenario does not match its recorded run")
    nexus = NexusState(**snapshot["nexus"])
    if nexus.coupling != record["nexus"]["coupling"]:
        raise ValueError("Demo physics does not match its recorded run")
    agents = {}
    footprint = NexusFootprint()
    for row in record["agents"]:
        agents[row["name"]] = AgentOutput(
            agent=row["name"], content=row["content"], tool_outputs=row["tool_outputs"],
            usage_input_tokens=row["tokens_in"], usage_output_tokens=row["tokens_out"],
            provider=row["provider"], model=row["reported_model"],
            meta={"attempts": row["attempts"], "done_reason": row["done_reason"]},
        )
        footprint.add(FootprintEntry(row["name"], row["provider"], row["reported_model"],
                                     row["tokens_in"], row["tokens_out"]))
    scenario = {**record["scenario"], "demo": "Recorded Claude outputs; synthetic climate; uncalibrated"}
    return ScenarioRunResult(scenario=scenario, nexus=nexus, footprint=footprint,
                             timings=record["timings_sec"], **agents)
