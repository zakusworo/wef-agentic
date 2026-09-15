"""Water-related tools — location-agnostic (Sleman OR custom city)."""
from __future__ import annotations

from typing import Any

from wef_agentic.data.openmeteo import aggregate_monthly, fetch_climate_for_location
from wef_agentic.physics.coupling import water_stress_fraction
from wef_agentic.physics.water_balance import (
    irrigation_demand_mm,
    scenario_apply_climate_change,
    thornthwaite_mather,
)
from wef_agentic.tools._common import resolve_or_raise
from wef_agentic.tools.registry import register


@register(
    name="get_climate_summary",
    description=(
        "Ambil ringkasan klimat historis untuk lokasi (preset 'sleman' atau "
        "kota apapun via Open-Meteo geocoding). Realtime jika belum di-cache."
    ),
    parameters={
        "type": "object",
        "properties": {
            "location_query": {"type": "string"},
            "year_start": {"type": "integer", "default": 1991},
            "year_end": {"type": "integer", "default": 2024},
        },
        "required": ["location_query"],
    },
)
def get_climate_summary(
    location_query: str,
    year_start: int = 1991,
    year_end: int = 2024,
) -> dict[str, Any]:
    location = resolve_or_raise(location_query)
    df = fetch_climate_for_location(location)
    monthly = aggregate_monthly(df)
    monthly = monthly[(monthly["year"] >= year_start) & (monthly["year"] <= year_end)]

    annual = (
        monthly.groupby(["station", "year"], as_index=False)
        .agg(precip_mm=("precip_mm", "sum"), tmean_c=("tmean_c", "mean"), et0_mm=("et0_mm", "sum"))
    )
    summary = (
        annual.groupby("station")
        .agg(
            precip_mean_mm=("precip_mm", "mean"),
            precip_std_mm=("precip_mm", "std"),
            tmean_c=("tmean_c", "mean"),
            et0_mean_mm=("et0_mm", "mean"),
        )
        .round(1)
        .to_dict(orient="index")
    )

    return {
        "location": location.to_dict(),
        "year_range": [year_start, year_end],
        "stations": summary,
    }


@register(
    name="run_water_balance",
    description=(
        "Jalankan Thornthwaite-Mather monthly water balance untuk lokasi. "
        "Returns surplus, deficit, water stress (1 - ETa/PET)."
    ),
    parameters={
        "type": "object",
        "properties": {
            "location_query": {"type": "string"},
            "station": {"type": "string"},
            "year": {"type": "integer", "default": 2023},
            "delta_precip_pct": {"type": "number", "default": 0.0},
            "delta_temp_c": {"type": "number", "default": 0.0},
            "soil_water_capacity_mm": {"type": "number", "default": 150.0},
        },
        "required": ["location_query"],
    },
)
def run_water_balance(
    location_query: str,
    station: str | None = None,
    year: int = 2023,
    delta_precip_pct: float = 0.0,
    delta_temp_c: float = 0.0,
    soil_water_capacity_mm: float = 150.0,
) -> dict[str, Any]:
    location = resolve_or_raise(location_query)
    df = fetch_climate_for_location(location)
    monthly = aggregate_monthly(df)

    effective_station = station or location.metadata.get("default_station", location.name)

    sub = monthly[(monthly["station"] == effective_station) & (monthly["year"] == year)].copy()
    if sub.empty:
        sub = monthly[monthly["year"] == year].copy()
        if sub.empty:
            raise ValueError(f"Tidak ada data untuk year={year} di lokasi {location.display}")
        effective_station = sub["station"].iloc[0]

    sub = sub.sort_values("month").reset_index(drop=True)
    sub = scenario_apply_climate_change(
        sub, delta_precip_pct=delta_precip_pct, delta_temp_c=delta_temp_c
    )
    result = thornthwaite_mather(sub, soil_water_capacity_mm=soil_water_capacity_mm)
    summary = result.annual_summary

    return {
        "location": location.to_dict(),
        "station": effective_station,
        "year": year,
        "delta_precip_pct": delta_precip_pct,
        "delta_temp_c": delta_temp_c,
        "soil_water_capacity_mm": soil_water_capacity_mm,
        "summary": {k: round(v, 3) for k, v in summary.items()},
        "water_stress_raw": round(
            water_stress_fraction(summary["total_eta_mm"], summary["total_pet_mm"]), 4
        ),
        "monthly": result.monthly[
            ["month", "precip_mm", "et0_mm", "eta_mm", "surplus_mm", "deficit_mm", "soil_moisture_mm"]
        ].round(1).to_dict(orient="records"),
    }


@register(
    name="compute_irrigation_demand",
    description="Convert moisture deficit (mm) ke kebutuhan air irigasi (mm) di lahan.",
    parameters={
        "type": "object",
        "properties": {
            "deficit_mm": {"type": "number"},
            "application_efficiency": {"type": "number", "default": 0.65},
        },
        "required": ["deficit_mm"],
    },
)
def compute_irrigation_demand(deficit_mm: float, application_efficiency: float = 0.65) -> dict:
    irr = irrigation_demand_mm(deficit_mm, application_efficiency)
    return {
        "deficit_mm": deficit_mm,
        "irrigation_demand_mm": round(irr, 1),
        "application_efficiency": application_efficiency,
    }
