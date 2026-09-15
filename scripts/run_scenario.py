"""Run one scenario end-to-end and save a reproducible run record.

Respects config/llm.yaml + env overrides (WEF_AGENTIC_PROVIDER_OVERRIDE,
WEF_AGENTIC_MODEL_OVERRIDE), loaded from .env.

Usage:
    python scripts/run_scenario.py S2_JETP_Aligned
    python scripts/run_scenario.py S1_BAU_2030 --location Bandung
    python scripts/run_scenario.py S2_JETP_Aligned --provider ollama-local --model llama3.2:1b

Output: docs/runs/run_<scenario>_<location>_<provider>_<timestamp>.json
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from datetime import UTC, datetime

from dotenv import load_dotenv

from wef_agentic.config.settings import ROOT

load_dotenv(ROOT / ".env")

from wef_agentic.agents.critic import format_checks  # noqa: E402
from wef_agentic.orchestration import build_run_record, get_scenario, run_scenario  # noqa: E402


def _print_event(phase: str, payload: dict) -> None:
    if phase == "nexus_done":
        print(f"\nNexus computed in {payload['elapsed']:.1f}s")
        print(format_checks(payload["checks"]))
        for w in payload["warnings"]:
            print(f"  ! {w}")
    elif phase == "agent_done":
        retry = f" ({payload['attempts']} attempts)" if payload["attempts"] > 1 else ""
        print(f"  {payload['agent']:12s} {payload['elapsed']:6.1f}s  "
              f"tokens in/out = {payload['input_tokens']}/{payload['output_tokens']}  "
              f"model={payload['model']}{retry}")
    elif phase.endswith("_start") and phase != "nexus_start":
        print(f"\n▶ {phase.removesuffix('_start')}")


async def main(args: argparse.Namespace) -> dict:
    scenario = get_scenario(args.scenario, location_query=args.location)
    print("=" * 70)
    print(f"WEF-Agentic run — {args.scenario} @ {scenario['location_query']}")
    print(f"Provider override : {os.environ.get('WEF_AGENTIC_PROVIDER_OVERRIDE') or '(yaml)'}")
    print(f"Model override    : {os.environ.get('WEF_AGENTIC_MODEL_OVERRIDE') or '(yaml)'}")
    print("=" * 70)

    result = await run_scenario(scenario, on_event=_print_event)

    est = result.footprint.estimate()
    print(f"\nTOTAL {result.timings['total']:.1f}s · {est['total_tokens']:,} tokens · "
          f"{est['energy_kwh']:.5f} kWh · {est['water_l']:.4f} L · {est['co2_kg'] * 1000:.2f} g CO₂eq")
    for note in est["notes"]:
        print(f"  note: {note}")
    print("\nCoordinator synthesis (first 800 chars):\n" + "─" * 70)
    print(result.coordinator.content[:800])
    return build_run_record(result, provider_override=os.environ.get("WEF_AGENTIC_PROVIDER_OVERRIDE"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("scenario", nargs="?", default="S2_JETP_Aligned")
    parser.add_argument("--location", default=None, help="override scenario location (default: sleman)")
    parser.add_argument("--provider", default=None, help="sets WEF_AGENTIC_PROVIDER_OVERRIDE")
    parser.add_argument("--model", default=None, help="sets WEF_AGENTIC_MODEL_OVERRIDE")
    cli = parser.parse_args()
    if cli.provider:
        os.environ["WEF_AGENTIC_PROVIDER_OVERRIDE"] = cli.provider
    if cli.model:
        os.environ["WEF_AGENTIC_MODEL_OVERRIDE"] = cli.model

    record = asyncio.run(main(cli))

    out_dir = ROOT / "docs" / "runs"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    provider = (record.get("provider_override") or "yaml").replace("/", "-")
    location = (record["scenario"].get("location_query") or "loc").lower().replace(" ", "-")
    out_path = out_dir / f"run_{cli.scenario}_{location}_{provider}_{ts}.json"
    out_path.write_text(json.dumps(record, indent=2, ensure_ascii=False))
    print(f"\n✓ Run record saved → {out_path.relative_to(ROOT)}")
