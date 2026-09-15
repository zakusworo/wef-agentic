"""Energy-related tools — location-agnostic."""
from __future__ import annotations

from typing import Any

from wef_agentic.data.bps_static import ELECTRICITY_CONSUMPTION
from wef_agentic.data.country_defaults import (
    ELECTRICITY_PER_CAPITA_KWH,
    GRID_EMISSION_FACTOR,
    get_default,
)
from wef_agentic.geo import Location
from wef_agentic.physics.energy_demand import SCENARIOS, compute_emissions, project_demand
from wef_agentic.tools._common import (
    resolve_or_raise,
    resolve_packet,
    resolve_population,
    sample_yearly,
    value_at,
)
from wef_agentic.tools.registry import register


def _proxy_baseline(location: Location) -> tuple[dict, list[dict]]:
    """Country per-capita consumption × local population, with provenance."""
    per_capita_packet = resolve_packet("energy.consumption_kwh_per_capita", location)
    provenance = []
    if per_capita_packet is not None:
        per_capita = float(per_capita_packet.value)
        provenance.append(per_capita_packet.to_dict())
    else:
        per_capita = float(get_default(ELECTRICITY_PER_CAPITA_KWH, location.country_code))
    population, pop_provenance = resolve_population(location)
    provenance.append(pop_provenance)
    return {
        "base_year": 2023,
        "base_demand_gwh": per_capita * population / 1e6,
        "base_population": population,
        "base_per_capita_kwh": per_capita,
        "base_pdrb_per_capita": None,
        "income_elasticity": 0.75,
        "pop_elasticity": 0.95,
    }, provenance


@register(
    name="get_electricity_history",
    description=(
        "Ambil data historis listrik. Sleman: BPS hardcoded. "
        "Lokasi lain: estimasi country-level × populasi (illustrative)."
    ),
    parameters={
        "type": "object",
        "properties": {"location_query": {"type": "string"}},
        "required": ["location_query"],
    },
)
def get_electricity_history(location_query: str) -> dict[str, Any]:
    location = resolve_or_raise(location_query)
    if location.has_local_data:
        packet = resolve_packet("energy.consumption_gwh_annual", location)
        return {
            "location": location.to_dict(),
            "unit": "GWh/year",
            "source": "BPS Sleman + ESDM",
            "data": ELECTRICITY_CONSUMPTION,
            "data_quality": "good (verified historical)",
            "provenance": [packet.to_dict()] if packet else [],
        }

    baseline, provenance = _proxy_baseline(location)
    return {
        "location": location.to_dict(),
        "unit": "GWh/year",
        "source": f"Country per-capita ({location.country_code}) × population",
        "per_capita_kwh": baseline["base_per_capita_kwh"],
        "population": baseline["base_population"],
        "data": {2023: round(baseline["base_demand_gwh"], 1)},
        "data_quality": "illustrative (country-level proxy, not local)",
        "provenance": provenance,
    }


@register(
    name="project_energy_demand",
    description="Project demand listrik ke horizon di bawah skenario.",
    parameters={
        "type": "object",
        "properties": {
            "location_query": {"type": "string"},
            "scenario": {
                "type": "string",
                "enum": list(SCENARIOS),
                "default": "BAU",
            },
            "horizon": {"type": "integer", "default": 2050},
            "extra_demand_at_horizon_gwh": {"type": "number", "default": 0.0},
        },
        "required": ["location_query"],
    },
)
def project_energy_demand_tool(
    location_query: str,
    scenario: str = "BAU",
    horizon: int = 2050,
    extra_demand_at_horizon_gwh: float = 0.0,
) -> dict[str, Any]:
    location = resolve_or_raise(location_query)

    baseline, provenance = (None, []) if location.has_local_data else _proxy_baseline(location)
    proj = project_demand(
        scenario=scenario,
        horizon=horizon,
        baseline=baseline,
        extra_demand_at_horizon_gwh=extra_demand_at_horizon_gwh,
    )
    yearly = proj.yearly

    return {
        "location": location.to_dict(),
        "scenario": scenario,
        "horizon": horizon,
        "assumptions": proj.assumptions,
        "data_quality": "good (BPS-anchored)" if location.has_local_data
        else "illustrative (country-level per-capita × population)",
        "endpoints": {
            "demand_base_gwh": value_at(yearly, proj.assumptions["base_year"], "demand_total_gwh"),
            "demand_2030_gwh": value_at(yearly, 2030, "demand_total_gwh"),
            "demand_2050_gwh": value_at(yearly, 2050, "demand_total_gwh"),
            "demand_horizon_gwh": value_at(yearly, horizon, "demand_total_gwh"),
            "irrigation_pumping_horizon_gwh": value_at(
                yearly, horizon, "demand_irrigation_pumping_gwh"
            ),
        },
        "yearly_summary": sample_yearly(yearly, ["year", "demand_total_gwh"]),
        "provenance": provenance,
    }


@register(
    name="estimate_emissions",
    description="Estimasi emisi CO2 (Mt) dari demand GWh + renewable share. Country-aware.",
    parameters={
        "type": "object",
        "properties": {
            "demand_gwh": {"type": "number"},
            "renewable_share": {"type": "number"},
            "country_code": {"type": "string", "default": "ID"},
            "grid_emission_factor": {"type": "number"},
        },
        "required": ["demand_gwh", "renewable_share"],
    },
)
def estimate_emissions_tool(
    demand_gwh: float,
    renewable_share: float,
    country_code: str = "ID",
    grid_emission_factor: float | None = None,
) -> dict[str, Any]:
    if grid_emission_factor is None:
        grid_emission_factor = get_default(GRID_EMISSION_FACTOR, country_code)
    mt = compute_emissions(demand_gwh, renewable_share, grid_emission_factor)
    return {
        "demand_gwh": demand_gwh,
        "renewable_share": renewable_share,
        "country_code": country_code,
        "grid_emission_factor_kg_co2_per_kwh": grid_emission_factor,
        "co2_emissions_mt": round(mt, 3),
    }


@register(
    name="list_energy_scenarios",
    description="List semua scenario energi + asumsinya.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def list_energy_scenarios() -> dict[str, Any]:
    return SCENARIOS
