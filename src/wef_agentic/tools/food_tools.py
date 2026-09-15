"""Food-related tools — location-agnostic.

Crop projections need a *local* harvest area. For locations without one (no BPS
preset, no manual override) the projection is reported as unavailable instead of
borrowing another region's farmland.
"""
from __future__ import annotations

from typing import Any

from wef_agentic.data.bps_static import RICE_HARVEST_AREA, RICE_YIELD
from wef_agentic.data.country_defaults import (
    POPULATION_GROWTH,
    RICE_PER_CAPITA_KG,
    get_default,
)
from wef_agentic.geo import Location
from wef_agentic.physics.crop_yield import (
    KY_VALUES,
    LP2B_LOSS_MULTIPLIER,
    compute_ssl,
    project_yield,
)
from wef_agentic.tools._common import (
    resolve_or_raise,
    resolve_packet,
    resolve_population,
    sample_yearly,
    value_at,
)
from wef_agentic.tools.registry import register


@register(
    name="get_food_history",
    description=(
        "Ambil data historis pertanian. Sleman: BPS asli. Lokasi lain: country "
        "FAOSTAT proxy notes."
    ),
    parameters={
        "type": "object",
        "properties": {"location_query": {"type": "string"}},
        "required": ["location_query"],
    },
)
def get_food_history(location_query: str) -> dict[str, Any]:
    location = resolve_or_raise(location_query)
    if location.has_local_data:
        return {
            "location": location.to_dict(),
            "rice_harvest_area_ha": RICE_HARVEST_AREA,
            "rice_yield_t_ha": RICE_YIELD,
            "trend_note": "Penurunan luas panen ~280 ha/tahun akibat alih fungsi LP2B",
            "data_quality": "good (BPS verified)",
        }

    per_capita_rice = get_default(RICE_PER_CAPITA_KG, location.country_code)
    return {
        "location": location.to_dict(),
        "rice_per_capita_kg": per_capita_rice,
        "note": (
            f"Local agriculture data tidak tersedia untuk {location.display}. "
            "FAOSTAT/national surveys diperlukan untuk analisis presisi."
        ),
        "data_quality": "illustrative (country-level FAOSTAT proxy)",
    }


def _unavailable(location: Location, crop: str, reason: str) -> dict[str, Any]:
    return {
        "available": False,
        "location": location.to_dict(),
        "crop": crop,
        "reason": reason,
        "data_quality": "unavailable",
    }


@register(
    name="project_crop_yield",
    description=(
        "Project produksi padi ke horizon dari luas panen lokal (BPS atau manual override). "
        "Tanpa luas panen lokal → available=false."
    ),
    parameters={
        "type": "object",
        "properties": {
            "location_query": {"type": "string"},
            "crop": {"type": "string", "enum": list(KY_VALUES), "default": "padi"},
            "scenario": {"type": "string", "default": "BAU"},
            "water_stress_fraction": {"type": "number", "default": 0.0},
            "lp2b_protection": {"type": "string",
                                "enum": list(LP2B_LOSS_MULTIPLIER), "default": "moderate"},
            "horizon": {"type": "integer", "default": 2050},
        },
        "required": ["location_query"],
    },
)
def project_crop_yield_tool(
    location_query: str,
    crop: str = "padi",
    scenario: str = "BAU",
    water_stress_fraction: float = 0.0,
    lp2b_protection: str = "moderate",
    horizon: int = 2050,
) -> dict[str, Any]:
    location = resolve_or_raise(location_query)

    if crop != "padi":
        return _unavailable(location, crop, "Hanya luas panen padi yang terdaftar (food.rice_area_ha).")

    area_packet = resolve_packet("food.rice_area_ha", location)
    if area_packet is None:
        return _unavailable(
            location, crop,
            f"Luas panen padi lokal untuk {location.display} tidak tersedia. Sediakan "
            f"'food.rice_area_ha' via data/external/override_{location.slug}.json.",
        )

    warnings = []
    provenance = [area_packet.to_dict()]
    loss_packet = resolve_packet("food.rice_land_loss_ha_per_year", location)
    if loss_packet is not None:
        annual_loss_ha = float(loss_packet.value)
        provenance.append(loss_packet.to_dict())
    else:
        annual_loss_ha = 0.0
        warnings.append("Laju alih fungsi lahan tidak tersedia — diasumsikan 0 ha/tahun.")
    yield_packet = resolve_packet("food.rice_yield_t_per_ha", location)
    if yield_packet is not None:
        provenance.append(yield_packet.to_dict())

    base_year = area_packet.year or 2023
    proj = project_yield(
        base_area_ha=float(area_packet.value),
        annual_loss_ha=annual_loss_ha,
        crop=crop,
        scenario=scenario,
        horizon=horizon,
        water_stress_fraction=water_stress_fraction,
        lp2b_protection=lp2b_protection,
        base_year=base_year,
    )
    yearly = proj.yearly

    return {
        "available": True,
        "location": location.to_dict(),
        "crop": crop,
        "scenario": scenario,
        "lp2b_protection": lp2b_protection,
        "water_stress_fraction": water_stress_fraction,
        "assumptions": proj.assumptions,
        "observed_yield_t_ha": float(yield_packet.value) if yield_packet else None,
        "data_quality": "good (BPS anchored)" if location.has_local_data
        else f"local input via {area_packet.source}",
        "endpoints": {
            "production_2030_t": value_at(yearly, 2030, "production_t"),
            "production_2050_t": value_at(yearly, 2050, "production_t"),
            "production_horizon_t": value_at(yearly, horizon, "production_t"),
            "area_horizon_ha": value_at(yearly, horizon, "area_ha"),
            "yield_t_ha": float(yearly["yield_t_ha"].iloc[0]),
        },
        "yearly_summary": sample_yearly(yearly),
        "provenance": provenance,
        "warnings": warnings,
    }


@register(
    name="compute_food_ssl",
    description="Hitung Self-Sufficiency Level (SSL). Per-capita demand country-aware.",
    parameters={
        "type": "object",
        "properties": {
            "production_t": {"type": "number"},
            "location_query": {"type": "string"},
            "year": {"type": "integer", "default": 2030},
            "per_capita_demand_kg": {"type": "number"},
            "pop_growth_pct": {"type": "number"},
        },
        "required": ["production_t", "location_query"],
    },
)
def compute_food_ssl_tool(
    production_t: float,
    location_query: str,
    year: int = 2030,
    per_capita_demand_kg: float | None = None,
    pop_growth_pct: float | None = None,
) -> dict[str, Any]:
    location = resolve_or_raise(location_query)
    population_base, pop_provenance = resolve_population(location)
    provenance = [pop_provenance]
    base_year = pop_provenance.get("year") or 2023

    if per_capita_demand_kg is None:
        packet = resolve_packet("food.rice_consumption_kg_per_capita", location)
        if packet is not None:
            per_capita_demand_kg = float(packet.value)
            provenance.append(packet.to_dict())
        else:
            per_capita_demand_kg = float(get_default(RICE_PER_CAPITA_KG, location.country_code))
    if pop_growth_pct is None:
        pop_growth_pct = float(get_default(POPULATION_GROWTH, location.country_code))

    pop_proj = int(population_base * (1 + pop_growth_pct / 100) ** max(0, year - base_year))
    ssl = compute_ssl(production_t, pop_proj, per_capita_demand_kg=per_capita_demand_kg)
    return {
        "location": location.to_dict(),
        "year": year,
        "production_t": production_t,
        "population_base": population_base,
        "population_base_year": base_year,
        "pop_growth_pct": pop_growth_pct,
        "population": pop_proj,
        "per_capita_demand_kg": per_capita_demand_kg,
        "ssl": round(ssl, 3),
        "interpretation": "Surplus" if ssl >= 1 else f"Defisit ({(1 - ssl) * 100:.1f}%)",
        "provenance": provenance,
    }
