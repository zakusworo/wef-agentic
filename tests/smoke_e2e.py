"""End-to-end smoke test — 5 agen + orchestration. Test Sleman + custom city."""
from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wef_agentic.agents import (
    CoordinatorAgent,
    CriticAgent,
    EnergyAgent,
    FoodAgent,
    WaterAgent,
)
from wef_agentic.llm.footprint import NexusFootprint
from wef_agentic.llm.ollama_provider import OllamaProvider
from wef_agentic.orchestration import get_scenario


async def run_scenario_with_override(scenario):
    """Run pipeline 5 agen dengan provider override (ollama-local llama3.2:1b)."""
    factory = lambda: OllamaProvider(model="llama3.2:1b", max_tokens=512, temperature=0.2)

    water = WaterAgent(provider=factory())
    energy = EnergyAgent(provider=factory())
    food = FoodAgent(provider=factory())
    critic = CriticAgent(provider=factory())
    coordinator = CoordinatorAgent(provider=factory())

    t0 = time.time()
    water_out, energy_out, food_out = await asyncio.gather(
        water.run(scenario),
        energy.run(scenario),
        food.run(scenario),
    )
    print(f"  Phase 1 (domain parallel): {time.time() - t0:.1f}s")

    t1 = time.time()
    critic_out = await critic.audit(scenario, water_out, energy_out, food_out)
    print(f"  Phase 2 (critic): {time.time() - t1:.1f}s")

    t2 = time.time()
    coord_out = await coordinator.synthesize(scenario, water_out, energy_out, food_out, critic_out)
    print(f"  Phase 3 (synthesis): {time.time() - t2:.1f}s")

    fp = NexusFootprint()
    for ai, ao in [(water, water_out), (energy, energy_out), (food, food_out),
                    (critic, critic_out), (coordinator, coord_out)]:
        fp.add(ai.to_footprint(ao))

    return water_out, energy_out, food_out, critic_out, coord_out, fp


async def test_sleman():
    print("=" * 60)
    print("TEST 1: Sleman preset (cached fixture, BPS data)")
    print("=" * 60)
    scenario = get_scenario("S2_JETP_Aligned")  # location_query=sleman default
    print(f"Scenario: {scenario['name']}, location: {scenario['location_query']}")
    print("-" * 60)
    *outputs, fp = await run_scenario_with_override(scenario)
    est = fp.estimate()
    print(f"  Total tokens: {est['total_tokens']:,} | "
          f"kWh: {est['energy_kwh']:.4f} | L: {est['water_l']:.3f}")
    print(f"  Coordinator preview: {outputs[-1].content[:200]}...")
    return est


async def test_custom_city(city: str):
    print("=" * 60)
    print(f"TEST 2: Custom city '{city}' (realtime Open-Meteo fetch)")
    print("=" * 60)
    scenario = get_scenario("S1_BAU_2030", location_query=city)
    print(f"Scenario: {scenario['name']}, location: {scenario['location_query']}")
    print("-" * 60)
    *outputs, fp = await run_scenario_with_override(scenario)
    est = fp.estimate()
    print(f"  Total tokens: {est['total_tokens']:,} | "
          f"kWh: {est['energy_kwh']:.4f} | L: {est['water_l']:.3f}")
    print(f"  Coordinator preview: {outputs[-1].content[:200]}...")
    return est


async def main():
    sleman_est = await test_sleman()
    print()

    # Test custom city - pakai Bandung (Indonesia) karena udah cached lat-lon
    # dekat dgn Sleman → fetch time relatif cepat
    bandung_est = await test_custom_city("Bandung")
    print()

    print("=" * 60)
    print("✓ E2E multi-city smoke test passed")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
