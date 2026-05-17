"""Energy-related tools — location-agnostic."""
from __future__ import annotations

from typing import Any

from wef_agentic.data.bps_static import ELECTRICITY_CONSUMPTION
from wef_agentic.data.country_defaults import (
    ELECTRICITY_PER_CAPITA_KWH,
    GRID_EMISSION_FACTOR,
    get_default,
)
from wef_agentic.geo import resolve_location
from wef_agentic.physics.energy_demand import SCENARIOS, compute_emissions, project_demand
from wef_agentic.tools.registry import register


def _resolve_or_raise(location_query: str):
    loc = resolve_location(location_query)
    if loc is None:
        raise ValueError(f"Tidak dapat resolve location: '{location_query}'")
    return loc


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
    location = _resolve_or_raise(location_query)
    if location.name == "Sleman" and location.source == "preset":
        return {
            "location": location.to_dict(),
            "unit": "GWh/year",
            "source": "BPS Sleman + ESDM",
            "data": ELECTRICITY_CONSUMPTION,
            "data_quality": "good (verified historical)",
        }

    per_capita = get_default(ELECTRICITY_PER_CAPITA_KWH, location.country_code)
    if location.population is None:
        pop = 100_000
        pop_note = " (population unknown, defaulted to 100k)"
    else:
        pop = location.population
        pop_note = ""
    base_demand_gwh = (per_capita * pop) / 1e6

    return {
        "location": location.to_dict(),
        "unit": "GWh/year",
        "source": f"Country average ({location.country_code}) × population{pop_note}",
        "per_capita_kwh": per_capita,
        "population": pop,
        "data": {2023: round(base_demand_gwh, 1)},
        "data_quality": "illustrative (country-level proxy, not local)",
    }


@register(
    name="project_energy_demand",
    description="Project demand listrik ke 2050 di bawah skenario.",
    parameters={
        "type": "object",
        "properties": {
            "location_query": {"type": "string"},
            "scenario": {
                "type": "string",
                "enum": ["BAU", "JETP_Aligned", "NetZero_Sleman_2045"],
                "default": "BAU",
            },
            "horizon": {"type": "integer", "default": 2050},
        },
        "required": ["location_query"],
    },
)
def project_energy_demand_tool(
    location_query: str,
    scenario: str = "BAU",
    horizon: int = 2050,
) -> dict[str, Any]:
    location = _resolve_or_raise(location_query)

    baseline = None
    if not (location.name == "Sleman" and location.source == "preset"):
        per_capita = get_default(ELECTRICITY_PER_CAPITA_KWH, location.country_code)
        pop = location.population or 100_000
        base_demand = (per_capita * pop) / 1e6
        baseline = {
            "base_year": 2023,
            "base_demand_gwh": base_demand,
            "base_population": pop,
            "base_pdrb_per_capita": 30.0,
            "income_elasticity": 0.75,
            "pop_elasticity": 0.95,
        }

    proj = project_demand(scenario=scenario, horizon=horizon, baseline=baseline)
    yearly = proj.yearly

    return {
        "location": location.to_dict(),
        "scenario": scenario,
        "horizon": horizon,
        "assumptions": proj.assumptions,
        "data_quality": "good (BPS-anchored)" if (
            location.name == "Sleman" and location.source == "preset"
        ) else "illustrative (country-level baseline)",
        "endpoints": {
            "demand_2030_gwh": float(yearly.loc[yearly["year"] == 2030, "demand_total_gwh"].iloc[0])
            if 2030 in yearly["year"].values else None,
            "demand_2050_gwh": float(yearly.loc[yearly["year"] == 2050, "demand_total_gwh"].iloc[0])
            if 2050 in yearly["year"].values else None,
        },
        "yearly_summary": yearly[["year", "demand_total_gwh"]]
            .iloc[:: max(1, len(yearly) // 6)]
            .round(1)
            .to_dict(orient="records"),
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
