"""Orchestration graph — Pattern A: scenario sweep.

Coordinator → (Water || Energy || Food) → Critic → Coordinator synthesis

Mendukung 2 mode:
- run_scenario() — full pipeline, parallel domain agents (fastest)
- run_scenario_staged() — split per-phase untuk live progress UI
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field

from wef_agentic.agents import (
    AgentOutput,
    CoordinatorAgent,
    CriticAgent,
    EnergyAgent,
    FoodAgent,
    WaterAgent,
)
from wef_agentic.llm.footprint import NexusFootprint


@dataclass
class ScenarioRunResult:
    scenario: dict
    water: AgentOutput
    energy: AgentOutput
    food: AgentOutput
    critic: AgentOutput
    coordinator: AgentOutput
    footprint: NexusFootprint
    timings: dict = field(default_factory=dict)


async def run_scenario(scenario: dict) -> ScenarioRunResult:
    """Execute full pipeline (parallel domain agents). Fastest mode."""
    water = WaterAgent()
    energy = EnergyAgent()
    food = FoodAgent()
    critic = CriticAgent()
    coordinator = CoordinatorAgent()

    t0 = time.time()
    water_out, energy_out, food_out = await asyncio.gather(
        water.run(scenario), energy.run(scenario), food.run(scenario),
    )
    t_domain = time.time() - t0

    t1 = time.time()
    critic_out = await critic.audit(scenario, water_out, energy_out, food_out)
    t_critic = time.time() - t1

    t2 = time.time()
    coord_out = await coordinator.synthesize(
        scenario, water_out, energy_out, food_out, critic_out
    )
    t_coord = time.time() - t2

    fp = NexusFootprint()
    for ai, ao in [
        (water, water_out), (energy, energy_out), (food, food_out),
        (critic, critic_out), (coordinator, coord_out),
    ]:
        fp.add(ai.to_footprint(ao))

    return ScenarioRunResult(
        scenario=scenario,
        water=water_out, energy=energy_out, food=food_out,
        critic=critic_out, coordinator=coord_out,
        footprint=fp,
        timings={"domain": t_domain, "critic": t_critic, "coordinator": t_coord,
                 "total": t_domain + t_critic + t_coord},
    )


# ─────────────────────────────────────────────────────────────────────────────
# Staged API — sub-phases callable terpisah untuk live logging di UI
# ─────────────────────────────────────────────────────────────────────────────


async def run_one_agent(agent_class, scenario: dict, **kwargs):
    """Generic single-agent runner. Returns (agent_instance, output, elapsed_s)."""
    instance = agent_class()
    t0 = time.time()
    output = await instance.run(scenario, **kwargs) if hasattr(instance, "run") else None
    elapsed = time.time() - t0
    return instance, output, elapsed


async def run_water(scenario: dict):
    """Phase: water agent only."""
    instance = WaterAgent()
    t0 = time.time()
    out = await instance.run(scenario)
    return instance, out, time.time() - t0


async def run_energy(scenario: dict):
    instance = EnergyAgent()
    t0 = time.time()
    out = await instance.run(scenario)
    return instance, out, time.time() - t0


async def run_food(scenario: dict):
    instance = FoodAgent()
    t0 = time.time()
    out = await instance.run(scenario)
    return instance, out, time.time() - t0


async def run_critic(scenario: dict, water_out, energy_out, food_out):
    instance = CriticAgent()
    t0 = time.time()
    out = await instance.audit(scenario, water_out, energy_out, food_out)
    return instance, out, time.time() - t0


async def run_coordinator(scenario: dict, water_out, energy_out, food_out, critic_out):
    instance = CoordinatorAgent()
    t0 = time.time()
    out = await instance.synthesize(scenario, water_out, energy_out, food_out, critic_out)
    return instance, out, time.time() - t0


def build_result(
    scenario: dict,
    water, water_out, energy, energy_out, food, food_out,
    critic, critic_out, coordinator, coord_out,
    timings: dict | None = None,
) -> ScenarioRunResult:
    """Helper untuk merakit ScenarioRunResult dari per-agent outputs."""
    fp = NexusFootprint()
    for ai, ao in [
        (water, water_out), (energy, energy_out), (food, food_out),
        (critic, critic_out), (coordinator, coord_out),
    ]:
        fp.add(ai.to_footprint(ao))

    return ScenarioRunResult(
        scenario=scenario,
        water=water_out, energy=energy_out, food=food_out,
        critic=critic_out, coordinator=coord_out,
        footprint=fp,
        timings=timings or {},
    )


async def run_scenario_sweep(scenarios: list[dict]) -> list[ScenarioRunResult]:
    """Run multiple scenarios sequentially."""
    results = []
    for sc in scenarios:
        result = await run_scenario(sc)
        results.append(result)
    return results
