"""Reproducible run records — everything needed to audit or re-run a scenario."""
from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from typing import Any

from wef_agentic.config.settings import ROOT, load_llm_config, load_nexus_config


def git_revision() -> dict[str, Any]:
    def _git(*args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True, timeout=10,
        ).stdout.strip()

    try:
        return {"sha": _git("rev-parse", "HEAD"), "dirty": bool(_git("status", "--porcelain"))}
    except (OSError, subprocess.SubprocessError):
        return {"sha": None, "dirty": None}


def _package_version() -> str | None:
    try:
        return version("wef-agentic")
    except PackageNotFoundError:
        return None


def build_run_record(result, **extra: Any) -> dict[str, Any]:
    """JSON-safe record of a ScenarioRunResult (full content, not previews)."""
    agents = []
    for output in (result.water, result.energy, result.food, result.critic, result.coordinator):
        meta = output.meta or {}
        agents.append({
            "name": output.agent,
            "provider": output.provider,
            "requested_model": meta.get("requested_model"),
            "reported_model": output.model,
            "tokens_in": output.usage_input_tokens,
            "tokens_out": output.usage_output_tokens,
            "attempts": meta.get("attempts"),
            "done_reason": meta.get("done_reason"),
            "truncated": meta.get("truncated"),
            "thinking_chars": meta.get("thinking_chars"),
            "system_prompt_sha256": meta.get("system_prompt_sha256"),
            "prompt_sha256": meta.get("prompt_sha256"),
            "content": output.content,
            "tool_outputs": output.tool_outputs,
        })

    record = {
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "git": git_revision(),
        "package_version": _package_version(),
        "scenario": result.scenario,
        "config": {"llm": load_llm_config(), "nexus": load_nexus_config()},
        "nexus": {
            "key_figures": result.nexus.key_figures(),
            "checks": result.nexus.checks,
            "warnings": result.nexus.warnings,
            "provenance": result.nexus.provenance,
            "coupling": result.nexus.coupling,
        },
        "agents": agents,
        "timings_sec": {k: round(v, 2) for k, v in result.timings.items()},
        "footprint": result.footprint.estimate(),
        **extra,
    }
    # Round-trip: stringify datetimes/numpy scalars, turn int dict keys into strings
    return json.loads(json.dumps(record, default=str))
