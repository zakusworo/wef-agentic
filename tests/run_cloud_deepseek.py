"""Production-grade run via Ollama Cloud (deepseek-v4-pro + kimi-k2.6).

Pakai factory `get_provider_for_agent()` supaya menghormati config/llm.yaml +
env override (WEF_AGENTIC_PROVIDER_OVERRIDE=ollama-cloud di .env).

Output: stdout transcript + JSON ringkasan ke docs/runs/.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

# Load .env early
try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass

from wef_agentic.agents import (
    CoordinatorAgent,
    CriticAgent,
    EnergyAgent,
    FoodAgent,
    WaterAgent,
)
from wef_agentic.llm.footprint import NexusFootprint
from wef_agentic.orchestration import get_scenario


async def main(scenario_id: str = "S2_JETP_Aligned") -> dict:
    provider_override = os.environ.get("WEF_AGENTIC_PROVIDER_OVERRIDE", "(yaml default)")
    model_override = os.environ.get("WEF_AGENTIC_MODEL_OVERRIDE", "(per-agent yaml)")

    print("=" * 70)
    print(f"WEF-Agentic E2E run — {scenario_id}")
    print(f"Provider override : {provider_override}")
    print(f"Model override    : {model_override}")
    print(f"Timestamp (UTC)   : {datetime.now(timezone.utc).isoformat()}")
    print("=" * 70)

    # Factory mengambil provider per-agent dari yaml (di-override env)
    water = WaterAgent()
    energy = EnergyAgent()
    food = FoodAgent()
    critic = CriticAgent()
    coordinator = CoordinatorAgent()

    print("\nAgents instantiated:")
    for ai in (water, energy, food, critic, coordinator):
        print(f"  {ai.name:14s} → {ai.provider.name:14s} model={ai.provider.model}")

    scenario = get_scenario(scenario_id)
    print(f"\nScenario: {scenario['name']}")
    print(f"Location: {scenario.get('location_query', '?')}")
    print("-" * 70)

    t0 = time.time()
    water_out, energy_out, food_out = await asyncio.gather(
        water.run(scenario),
        energy.run(scenario),
        food.run(scenario),
    )
    phase1 = time.time() - t0
    print(f"\nPhase 1 (water || energy || food, parallel): {phase1:.1f}s")
    for ai, ao in [(water, water_out), (energy, energy_out), (food, food_out)]:
        print(f"  {ai.name:8s} tokens in/out = {ao.usage_input_tokens}/{ao.usage_output_tokens}")

    t1 = time.time()
    critic_out = await critic.audit(scenario, water_out, energy_out, food_out)
    phase2 = time.time() - t1
    print(f"\nPhase 2 (critic audit): {phase2:.1f}s")
    print(f"  critic   tokens in/out = {critic_out.usage_input_tokens}/{critic_out.usage_output_tokens}")

    t2 = time.time()
    coord_out = await coordinator.synthesize(scenario, water_out, energy_out, food_out, critic_out)
    phase3 = time.time() - t2
    print(f"\nPhase 3 (coordinator synthesize): {phase3:.1f}s")
    print(f"  coord    tokens in/out = {coord_out.usage_input_tokens}/{coord_out.usage_output_tokens}")

    total = time.time() - t0
    print(f"\n{'─' * 70}")
    print(f"TOTAL elapsed: {total:.1f}s  ({total / 60:.2f} min)")

    fp = NexusFootprint()
    for ai, ao in [(water, water_out), (energy, energy_out), (food, food_out),
                   (critic, critic_out), (coordinator, coord_out)]:
        fp.add(ai.to_footprint(ao))
    est = fp.estimate()
    print(f"\nNexus footprint:")
    print(f"  Total tokens : {est['total_tokens']:,}")
    print(f"  Energy       : {est['energy_kwh']:.6f} kWh")
    print(f"  Water        : {est['water_l']:.6f} L")
    print(f"  CO2eq        : {est['co2_kg']:.6f} kg")

    print(f"\nCoordinator synthesis (first 800 chars):")
    print("─" * 70)
    print((coord_out.content or "(empty)")[:800])
    print("─" * 70)

    print(f"\nCritic audit (first 600 chars):")
    print("─" * 70)
    print((critic_out.content or "(empty)")[:600])
    print("─" * 70)

    summary = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "scenario": {"id": scenario_id, "name": scenario["name"], "location": scenario.get("location_query")},
        "provider_override": provider_override,
        "agents": [
            {
                "name": ai.name,
                "provider": ai.provider.name,
                "model": ai.provider.model,
                "tokens_in": ao.usage_input_tokens,
                "tokens_out": ao.usage_output_tokens,
                "tool_calls": len(ao.tool_outputs),
            }
            for ai, ao in [
                (water, water_out), (energy, energy_out), (food, food_out),
                (critic, critic_out), (coordinator, coord_out),
            ]
        ],
        "timings_sec": {
            "phase1_parallel_domain": round(phase1, 2),
            "phase2_critic": round(phase2, 2),
            "phase3_coordinator": round(phase3, 2),
            "total": round(total, 2),
        },
        "footprint": est,
        "coordinator_preview": (coord_out.content or "")[:1500],
        "critic_preview": (critic_out.content or "")[:1500],
    }
    return summary


if __name__ == "__main__":
    scenario_id = sys.argv[1] if len(sys.argv) > 1 else "S2_JETP_Aligned"
    result = asyncio.run(main(scenario_id))

    out_dir = ROOT / "docs" / "runs"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"run_{scenario_id}_deepseek_cloud_{ts}.json"
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"\n✓ Summary saved → {out_path.relative_to(ROOT)}")
