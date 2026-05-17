"""Variable registry — kanonik untuk variable yang dipakai agen.

JSON schema-compatible untuk manual override.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class VariableSpec:
    name: str
    description: str
    unit: str
    domain: str  # "climate" | "socio" | "energy" | "food" | "grid"
    schema: dict  # JSON schema for value


VARIABLES: dict[str, VariableSpec] = {
    # ── Climate ──
    "climate.precip_mm_annual": VariableSpec(
        name="climate.precip_mm_annual",
        description="Total presipitasi tahunan rata-rata (mm/year)",
        unit="mm/year",
        domain="climate",
        schema={"type": "number", "minimum": 0, "maximum": 10000},
    ),
    "climate.temp_c_mean": VariableSpec(
        name="climate.temp_c_mean",
        description="Suhu tahunan rata-rata (°C)",
        unit="°C",
        domain="climate",
        schema={"type": "number", "minimum": -40, "maximum": 50},
    ),
    "climate.et0_mm_annual": VariableSpec(
        name="climate.et0_mm_annual",
        description="Reference evapotranspiration tahunan (mm/year, FAO-56)",
        unit="mm/year",
        domain="climate",
        schema={"type": "number", "minimum": 0, "maximum": 5000},
    ),

    # ── Socio-economic ──
    "socio.population": VariableSpec(
        name="socio.population",
        description="Populasi total (jiwa)",
        unit="jiwa",
        domain="socio",
        schema={"type": "integer", "minimum": 0},
    ),
    "socio.gdp_per_capita_usd": VariableSpec(
        name="socio.gdp_per_capita_usd",
        description="PDB per kapita (USD nominal, tahun terkini)",
        unit="USD",
        domain="socio",
        schema={"type": "number", "minimum": 0},
    ),

    # ── Energy ──
    "energy.consumption_kwh_per_capita": VariableSpec(
        name="energy.consumption_kwh_per_capita",
        description="Konsumsi listrik per kapita tahunan (kWh)",
        unit="kWh/year",
        domain="energy",
        schema={"type": "number", "minimum": 0},
    ),
    "energy.consumption_gwh_annual": VariableSpec(
        name="energy.consumption_gwh_annual",
        description="Konsumsi listrik total tahunan untuk wilayah (GWh)",
        unit="GWh/year",
        domain="energy",
        schema={"type": "number", "minimum": 0},
    ),
    "energy.renewable_share": VariableSpec(
        name="energy.renewable_share",
        description="Fraksi EBT dalam grid mix (0-1)",
        unit="ratio",
        domain="energy",
        schema={"type": "number", "minimum": 0, "maximum": 1},
    ),

    # ── Food ──
    "food.rice_consumption_kg_per_capita": VariableSpec(
        name="food.rice_consumption_kg_per_capita",
        description="Konsumsi beras per kapita tahunan (kg)",
        unit="kg/year",
        domain="food",
        schema={"type": "number", "minimum": 0, "maximum": 300},
    ),
    "food.rice_area_ha": VariableSpec(
        name="food.rice_area_ha",
        description="Luas panen padi (ha)",
        unit="ha",
        domain="food",
        schema={"type": "number", "minimum": 0},
    ),
    "food.rice_yield_t_per_ha": VariableSpec(
        name="food.rice_yield_t_per_ha",
        description="Produktivitas padi (ton/ha)",
        unit="t/ha",
        domain="food",
        schema={"type": "number", "minimum": 0, "maximum": 15},
    ),

    # ── Grid ──
    "grid.emission_factor_kg_co2_per_kwh": VariableSpec(
        name="grid.emission_factor_kg_co2_per_kwh",
        description="Emisi grid (kg CO2/kWh)",
        unit="kg CO2/kWh",
        domain="grid",
        schema={"type": "number", "minimum": 0, "maximum": 2},
    ),
}


def list_variables(domain: str | None = None) -> list[VariableSpec]:
    if domain is None:
        return list(VARIABLES.values())
    return [v for v in VARIABLES.values() if v.domain == domain]


def get_variable(name: str) -> VariableSpec:
    if name not in VARIABLES:
        raise KeyError(f"Unknown variable: {name}. Available: {list(VARIABLES)}")
    return VARIABLES[name]


def manual_override_schema() -> dict:
    """JSON schema untuk file upload manual override."""
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "WEF-Agentic Manual Data Override",
        "type": "object",
        "properties": {
            "version": {"type": "string", "const": "1.0"},
            "location": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "lat": {"type": "number"},
                    "lon": {"type": "number"},
                    "country_code": {"type": "string"},
                },
                "required": ["name"],
            },
            "variables": {
                "type": "object",
                "additionalProperties": {
                    "type": "object",
                    "properties": {
                        "value": {},
                        "year": {"type": "integer"},
                        "source": {"type": "string"},
                        "note": {"type": "string"},
                    },
                    "required": ["value", "source"],
                },
            },
        },
        "required": ["version", "variables"],
    }
