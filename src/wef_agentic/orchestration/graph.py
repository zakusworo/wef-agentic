"""Orchestration graph — Pattern A: scenario sweep.

    compute_nexus (deterministic, off the event loop)
      → Water || Energy || Food  (parallel LLM interpretation)
      → Critic (audits narratives against key figures + checks)
      → Coordinator synthesis
"""
from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from wef_agentic.agents import (
    AgentOutput,
    CoordinatorAgent,
    CriticAgent,
    EnergyAgent,
    FoodAgent,
    WaterAgent,
)
from wef_agentic.geo import Location
from wef_agentic.llm.footprint import NexusFootprint
from wef_agentic.orchestration.nexus import NexusState, compute_nexus

EventCallback = Callable[[str, dict[str, Any]], None]


@dataclass
class ScenarioRunResult:
    scenario: dict
    nexus: NexusState
    water: AgentOutput
    energy: AgentOutput
    food: AgentOutput
    critic: AgentOutput
    coordinator: AgentOutput
    footprint: NexusFootprint
    timings: dict = field(default_factory=dict)


def _agent_event(output: AgentOutput, elapsed: float) -> dict[str, Any]:
    return {
        "agent": output.agent,
        "elapsed": elapsed,
        "input_tokens": output.usage_input_tokens,
        "output_tokens": output.usage_output_tokens,
        "model": output.model,
        "attempts": output.meta.get("attempts", 1),
    }


async def _timed(coro):
    t0 = time.perf_counter()
    out = await coro
    return out, time.perf_counter() - t0


async def run_scenario(
    scenario: dict,
    *,
    location: Location | None = None,
    on_event: EventCallback | None = None,
) -> ScenarioRunResult:
    """Execute the full pipeline. `on_event(phase, payload)` receives progress updates."""
    emit = on_event or (lambda _phase, _payload: None)

    # Instantiate first so provider misconfiguration fails before slow data fetches
    water, energy, food = WaterAgent(), EnergyAgent(), FoodAgent()
    critic, coordinator = CriticAgent(), CoordinatorAgent()

    t_start = time.perf_counter()
    emit("nexus_start", {"location_query": scenario.get("location_query")})
    nexus = await asyncio.to_thread(compute_nexus, scenario, location)
    t_nexus = time.perf_counter() - t_start
    emit("nexus_done", {"elapsed": t_nexus, "checks": nexus.checks, "warnings": nexus.warnings})

    emit("domain_start", {})
    t0 = time.perf_counter()
    (water_out, dt_w), (energy_out, dt_e), (food_out, dt_f) = await asyncio.gather(
        _timed(water.run(scenario, nexus)),
        _timed(energy.run(scenario, nexus)),
        _timed(food.run(scenario, nexus)),
    )
    t_domain = time.perf_counter() - t0
    for out, dt in ((water_out, dt_w), (energy_out, dt_e), (food_out, dt_f)):
        emit("agent_done", _agent_event(out, dt))

    emit("critic_start", {})
    critic_out, t_critic = await _timed(
        critic.audit(scenario, water_out, energy_out, food_out, nexus)
    )
    emit("agent_done", _agent_event(critic_out, t_critic))

    emit("coordinator_start", {})
    coord_out, t_coord = await _timed(
        coordinator.synthesize(scenario, water_out, energy_out, food_out, critic_out, nexus)
    )
    emit("agent_done", _agent_event(coord_out, t_coord))

    fp = NexusFootprint()
    for agent, output in [
        (water, water_out), (energy, energy_out), (food, food_out),
        (critic, critic_out), (coordinator, coord_out),
    ]:
        fp.add(agent.to_footprint(output))

    timings = {
        "nexus": t_nexus, "domain": t_domain, "critic": t_critic, "coordinator": t_coord,
        "water": dt_w, "energy": dt_e, "food": dt_f,
        "total": time.perf_counter() - t_start,
    }
    emit("done", {"timings": timings, "total_tokens": fp.total_tokens})

    return ScenarioRunResult(
        scenario=scenario, nexus=nexus,
        water=water_out, energy=energy_out, food=food_out,
        critic=critic_out, coordinator=coord_out,
        footprint=fp, timings=timings,
    )


async def run_scenario_sweep(scenarios: list[dict]) -> list[ScenarioRunResult]:
    """Run multiple scenarios sequentially."""
    return [await run_scenario(sc) for sc in scenarios]
