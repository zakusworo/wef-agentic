"""Quick smoke — just Sleman (cached fixture)."""
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


async def main():
    factory = lambda: OllamaProvider(model="llama3.2:1b", max_tokens=512, temperature=0.2)

    water = WaterAgent(provider=factory())
    energy = EnergyAgent(provider=factory())
    food = FoodAgent(provider=factory())
    critic = CriticAgent(provider=factory())
    coordinator = CoordinatorAgent(provider=factory())

    scenario = get_scenario("S2_JETP_Aligned")
    print(f"Scenario: {scenario['name']}, location: {scenario['location_query']}")
    print("-" * 60)

    t0 = time.time()
    water_out, energy_out, food_out = await asyncio.gather(
        water.run(scenario), energy.run(scenario), food.run(scenario),
    )
    print(f"Phase 1 (parallel): {time.time() - t0:.1f}s")

    t1 = time.time()
    critic_out = await critic.audit(scenario, water_out, energy_out, food_out)
    print(f"Phase 2 (critic): {time.time() - t1:.1f}s")

    t2 = time.time()
    coord_out = await coordinator.synthesize(scenario, water_out, energy_out, food_out, critic_out)
    print(f"Phase 3 (coordinator): {time.time() - t2:.1f}s")

    print(f"\nTotal elapsed: {time.time() - t0:.1f}s")

    fp = NexusFootprint()
    for ai, ao in [(water, water_out), (energy, energy_out), (food, food_out),
                    (critic, critic_out), (coordinator, coord_out)]:
        fp.add(ai.to_footprint(ao))

    est = fp.estimate()
    print(f"\nNexus footprint:")
    print(f"  Total tokens: {est['total_tokens']:,}")
    print(f"  Energy: {est['energy_kwh']:.4f} kWh")
    print(f"  Water:  {est['water_l']:.4f} L")
    print(f"  CO2eq:  {est['co2_kg']:.4f} kg")

    print(f"\nCoordinator preview:")
    print(coord_out.content[:300])
    print("\n✓ E2E Sleman smoke passed")


if __name__ == "__main__":
    asyncio.run(main())
