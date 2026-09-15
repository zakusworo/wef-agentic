"""Crop yield — Doorenbos-Kassam (1979) water response.

Ya / Ymax = 1 - Ky × (1 - ETa / ETmax)

Cocok untuk water-yield-link MVP; AquaCrop-OS akan menggantikan di Phase 2.
Modul ini location-agnostic: luas panen & laju alih fungsi lahan wajib diberikan
oleh pemanggil (lihat tools/food_tools.py) — tidak ada default Sleman di sini.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

# Ky coefficient — Doorenbos & Kassam (1979) Table FAO 33
KY_VALUES = {
    "padi": 1.10,    # rice, sangat sensitif terhadap stress air
    "jagung": 1.25,  # maize, juga sensitif
}

# Maximum (water-unstressed) yield, t/ha — asumsi varietas dominan Jawa
# (Ciherang, Inpari padi; jagung hibrida). Ganti untuk wilayah lain.
YMAX = {
    "padi": 7.0,
    "jagung": 6.5,
}

# Pengali laju alih fungsi lahan terhadap laju historis, per tingkat proteksi LP2B
LP2B_LOSS_MULTIPLIER = {
    "strict": 0.3,
    "moderate": 1.0,
    "lax": 1.8,
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
    *,
    base_area_ha: float,
    annual_loss_ha: float,
    crop: str = "padi",
    scenario: str = "BAU",
    horizon: int = 2050,
    water_stress_fraction: float = 0.0,
    lp2b_protection: str = "moderate",
    base_year: int = 2023,
    ymax_t_ha: float | None = None,
) -> YieldProjection:
    """Project produksi tahunan dengan asumsi alih fungsi lahan.

    Args:
        base_area_ha: luas panen pada base_year (dari data lokal, bukan default)
        annual_loss_ha: laju historis alih fungsi lahan (ha/tahun)
        crop: 'padi' atau 'jagung'
        scenario: label skenario (hanya dicatat di assumptions)
        horizon: tahun akhir proyeksi
        water_stress_fraction: 1 - ETa/ETmax musim tanam (dari water balance coupling)
        lp2b_protection: 'strict' | 'moderate' | 'lax' — pengali laju alih fungsi
    """
    if crop not in KY_VALUES:
        raise ValueError(f"Unknown crop: {crop}")
    if lp2b_protection not in LP2B_LOSS_MULTIPLIER:
        raise ValueError(f"Unknown lp2b_protection: {lp2b_protection}")

    effective_loss_ha = annual_loss_ha * LP2B_LOSS_MULTIPLIER[lp2b_protection]
    ymax = ymax_t_ha if ymax_t_ha is not None else YMAX[crop]
    ratio = yield_ratio(eta_mm=(1 - water_stress_fraction), etmax_mm=1.0, crop=crop)
    yield_t_ha = ymax * ratio

    rows = []
    for i, yr in enumerate(range(base_year, horizon + 1)):
        area_ha = max(0.0, base_area_ha - i * effective_loss_ha)
        rows.append(
            {
                "year": yr,
                "area_ha": area_ha,
                "yield_t_ha": yield_t_ha,
                "production_t": area_ha * yield_t_ha,
            }
        )

    return YieldProjection(
        yearly=pd.DataFrame(rows),
        crop=crop,
        scenario=scenario,
        assumptions={
            "base_year": base_year,
            "base_area_ha": base_area_ha,
            "lp2b_protection": lp2b_protection,
            "annual_loss_ha": effective_loss_ha,
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
