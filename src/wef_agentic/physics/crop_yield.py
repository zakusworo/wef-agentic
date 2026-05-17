"""Crop yield — Doorenbos-Kassam (1979) water response.

Ya / Ymax = 1 - Ky × (1 - ETa / ETmax)

Cocok untuk water-yield-link MVP; AquaCrop-OS akan menggantikan di Phase 2.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from wef_agentic.data.bps_static import RICE_HARVEST_AREA, RICE_LAND_LOSS_PER_YEAR

# Ky coefficient — Doorenbos & Kassam (1979) Table FAO 33
KY_VALUES = {
    "padi": 1.10,    # rice, sangat sensitif terhadap stress air
    "jagung": 1.25,  # maize, juga sensitif
}

# Maximum yield (ton/ha) — varietas dominan Sleman (Ciherang, Inpari padi; jagung hibrida)
YMAX = {
    "padi": 7.0,
    "jagung": 6.5,
}


@dataclass
class YieldProjection:
    yearly: pd.DataFrame
    crop: str
    scenario: str
    assumptions: dict


def yield_ratio(eta_mm: float, etmax_mm: float, crop: str = "padi") -> float:
    """Doorenbos-Kassam yield response ratio (0-1)."""
    ky = KY_VALUES.get(crop, 1.0)
    if etmax_mm <= 0:
        return 0.0
    ratio = 1 - ky * (1 - eta_mm / etmax_mm)
    return max(0.0, min(1.0, ratio))


def project_yield(
    crop: str = "padi",
    scenario: str = "BAU",
    horizon: int = 2050,
    water_stress_fraction: float = 0.0,
    lp2b_protection: str = "moderate",
) -> YieldProjection:
    """Project produksi tahunan padi/jagung dengan asumsi alih fungsi lahan.

    Args:
        crop: 'padi' atau 'jagung'
        scenario: 'BAU' | 'JETP_Aligned' | 'NetZero_Sleman_2045'
        horizon: tahun akhir proyeksi
        water_stress_fraction: 0-1, mewakili rata-rata defisit air relatif (dari water balance)
        lp2b_protection: 'strict' | 'moderate' | 'lax' — kontrol alih fungsi
    """
    if crop not in KY_VALUES:
        raise ValueError(f"Unknown crop: {crop}")

    base_year = 2023
    base_area = RICE_HARVEST_AREA[base_year]

    # Land loss rate per skenario
    land_loss_map = {
        "strict": RICE_LAND_LOSS_PER_YEAR * 0.3,
        "moderate": RICE_LAND_LOSS_PER_YEAR * 1.0,
        "lax": RICE_LAND_LOSS_PER_YEAR * 1.8,
    }
    annual_loss_ha = land_loss_map.get(lp2b_protection, RICE_LAND_LOSS_PER_YEAR)

    ymax = YMAX[crop]
    ratio = yield_ratio(
        eta_mm=(1 - water_stress_fraction),
        etmax_mm=1.0,
        crop=crop,
    )
    yield_t_ha = ymax * ratio

    rows = []
    for i, yr in enumerate(range(base_year, horizon + 1)):
        area_ha = max(0, base_area - i * annual_loss_ha)
        production = area_ha * yield_t_ha
        rows.append(
            {
                "year": yr,
                "area_ha": area_ha,
                "yield_t_ha": yield_t_ha,
                "production_t": production,
            }
        )

    df = pd.DataFrame(rows)

    return YieldProjection(
        yearly=df,
        crop=crop,
        scenario=scenario,
        assumptions={
            "lp2b_protection": lp2b_protection,
            "annual_loss_ha": annual_loss_ha,
            "water_stress_fraction": water_stress_fraction,
            "ymax": ymax,
            "ky": KY_VALUES[crop],
        },
    )


def compute_ssl(production_t: float, population: int, per_capita_demand_kg: float = 115.0) -> float:
    """Self-Sufficiency Level (SSL).

    Standar konsumsi beras Indonesia ~115 kg/kapita/tahun (FAOSTAT, Kementan).
    SSL > 1 = surplus, < 1 = defisit.
    """
    if population <= 0:
        return 0.0
    demand_t = population * per_capita_demand_kg / 1000
    return production_t / demand_t if demand_t > 0 else 0.0
