"""Food-related tools — location-agnostic."""
from __future__ import annotations

from typing import Any

from wef_agentic.data.bps_static import POPULATION, RICE_HARVEST_AREA, RICE_YIELD
from wef_agentic.data.country_defaults import RICE_PER_CAPITA_KG, get_default
from wef_agentic.geo import resolve_location
from wef_agentic.physics.crop_yield import compute_ssl, project_yield
from wef_agentic.tools.registry import register


def _resolve_or_raise(location_query: str):
    loc = resolve_location(location_query)
    if loc is None:
        raise ValueError(f"Tidak dapat resolve location: '{location_query}'")
    return loc


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
    location = _resolve_or_raise(location_query)
    if location.name == "Sleman" and location.source == "preset":
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


@register(
    name="project_crop_yield",
    description="Project produksi padi/jagung ke horizon. Sleman: data lokal. Lokasi lain: caveat.",
    parameters={
        "type": "object",
        "properties": {
            "location_query": {"type": "string"},
            "crop": {"type": "string", "enum": ["padi", "jagung"], "default": "padi"},
            "scenario": {
                "type": "string",
                "enum": ["BAU", "JETP_Aligned", "NetZero_Sleman_2045"],
                "default": "BAU",
            },
            "water_stress_fraction": {"type": "number", "default": 0.0},
            "lp2b_protection": {"type": "string",
                                "enum": ["strict", "moderate", "lax"], "default": "moderate"},
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
    location = _resolve_or_raise(location_query)

    proj = project_yield(
        crop=crop,
        scenario=scenario,
        horizon=horizon,
        water_stress_fraction=water_stress_fraction,
        lp2b_protection=lp2b_protection,
    )
    yearly = proj.yearly
    end_year = horizon

    is_local = location.name == "Sleman" and location.source == "preset"

    return {
        "location": location.to_dict(),
        "crop": crop,
        "scenario": scenario,
        "lp2b_protection": lp2b_protection,
        "water_stress_fraction": water_stress_fraction,
        "assumptions": proj.assumptions,
        "data_quality": "good (BPS Sleman anchored)" if is_local else
                         "illustrative (Sleman parameters proxied to other location)",
        "endpoints": {
            "production_2030_t": float(yearly.loc[yearly["year"] == 2030, "production_t"].iloc[0])
            if 2030 in yearly["year"].values else None,
            "production_2050_t": float(yearly.loc[yearly["year"] == end_year, "production_t"].iloc[0])
            if end_year in yearly["year"].values else None,
            "area_2050_ha": float(yearly.loc[yearly["year"] == end_year, "area_ha"].iloc[0])
            if end_year in yearly["year"].values else None,
        },
        "yearly_summary": yearly.iloc[:: max(1, len(yearly) // 6)]
            .round(1)
            .to_dict(orient="records"),
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
        },
        "required": ["production_t", "location_query"],
    },
)
def compute_food_ssl_tool(
    production_t: float,
    location_query: str,
    year: int = 2030,
    per_capita_demand_kg: float | None = None,
) -> dict[str, Any]:
    location = _resolve_or_raise(location_query)
    if per_capita_demand_kg is None:
        per_capita_demand_kg = get_default(RICE_PER_CAPITA_KG, location.country_code)

    if location.name == "Sleman" and location.source == "preset":
        base_year, base_pop = 2023, POPULATION[2023]
    else:
        base_year, base_pop = 2023, (location.population or 100_000)

    pop_growth = 0.006
    years_ahead = max(0, year - base_year)
    pop_proj = int(base_pop * (1 + pop_growth) ** years_ahead)

    ssl = compute_ssl(production_t, pop_proj, per_capita_demand_kg=per_capita_demand_kg)
    return {
        "location": location.to_dict(),
        "year": year,
        "production_t": production_t,
        "population": pop_proj,
        "per_capita_demand_kg": per_capita_demand_kg,
        "ssl": round(ssl, 3),
        "interpretation": "Surplus" if ssl >= 1 else f"Defisit ({(1 - ssl) * 100:.1f}%)",
    }
