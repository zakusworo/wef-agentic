"""Energy demand projection — log-linear elasticity model.

D(t) = D(t0) × (POP(t)/POP(t0))^α × (GDPpc(t)/GDPpc(t0))^β × efficiency_factor

Estimasi α & β:
- α (income elasticity) ~ 0.6–0.9 untuk Indonesia (PLN/ESDM studies)
- β (population elasticity) ~ 0.8–1.0
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from wef_agentic.data.bps_static import (
    ELECTRICITY_CONSUMPTION,
    PDRB_PER_CAPITA,
    POPULATION,
)


@dataclass
class EnergyProjection:
    yearly: pd.DataFrame
    scenario: str
    assumptions: dict


def fit_elasticity_baseline(
    income_elasticity: float = 0.75,
    pop_elasticity: float = 0.95,
) -> dict:
    """Anchor baseline 2023 dari BPS static + tetapkan elasticity params."""
    return {
        "base_year": 2023,
        "base_demand_gwh": ELECTRICITY_CONSUMPTION[2023],
        "base_population": POPULATION[2023],
        "base_pdrb_per_capita": PDRB_PER_CAPITA[2023],
        "income_elasticity": income_elasticity,
        "pop_elasticity": pop_elasticity,
    }


SCENARIOS = {
    "BAU": {
        "pop_growth_pct": 0.6,        # %/tahun
        "gdp_pc_growth_pct": 4.5,
        "efficiency_gain_pct": 0.5,    # %/tahun perbaikan efisiensi
        "ev_share_target_2050": 0.10,
        "induction_share_target_2050": 0.20,
        "renewable_share_2030": 0.23,  # mengikuti RUPTL existing
    },
    "JETP_Aligned": {
        "pop_growth_pct": 0.6,
        "gdp_pc_growth_pct": 5.0,
        "efficiency_gain_pct": 1.0,
        "ev_share_target_2050": 0.40,
        "induction_share_target_2050": 0.50,
        "renewable_share_2030": 0.34,  # JETP CIPP target
    },
    "NetZero_Sleman_2045": {
        "pop_growth_pct": 0.5,
        "gdp_pc_growth_pct": 5.5,
        "efficiency_gain_pct": 1.5,
        "ev_share_target_2050": 0.80,
        "induction_share_target_2050": 0.95,
        "renewable_share_2030": 0.45,
    },
}


def project_demand(
    scenario: str = "BAU",
    horizon: int = 2050,
    baseline: dict | None = None,
) -> EnergyProjection:
    """Project demand tahunan dari base year ke horizon."""
    if scenario not in SCENARIOS:
        raise ValueError(f"Unknown scenario: {scenario}. Available: {list(SCENARIOS)}")

    base = baseline or fit_elasticity_baseline()
    s = SCENARIOS[scenario]

    base_year = base["base_year"]
    years = list(range(base_year, horizon + 1))

    pop_g = s["pop_growth_pct"] / 100
    gdp_g = s["gdp_pc_growth_pct"] / 100
    eff_g = s["efficiency_gain_pct"] / 100
    alpha = base["income_elasticity"]
    beta = base["pop_elasticity"]

    rows = []
    for i, yr in enumerate(years):
        pop_factor = (1 + pop_g) ** i
        gdp_factor = (1 + gdp_g) ** i
        eff_factor = (1 - eff_g) ** i  # efficiency reduces demand

        demand = (
            base["base_demand_gwh"]
            * (pop_factor**beta)
            * (gdp_factor**alpha)
            * eff_factor
        )

        # Tambahan demand dari elektrifikasi (EV, induction) — linear toward target 2050
        progress = (yr - base_year) / (2050 - base_year)
        progress = min(max(progress, 0), 1)
        ev_demand_gwh = base["base_demand_gwh"] * 0.05 * s["ev_share_target_2050"] * progress
        induction_demand_gwh = (
            base["base_demand_gwh"] * 0.03 * s["induction_share_target_2050"] * progress
        )

        total_demand = demand + ev_demand_gwh + induction_demand_gwh

        rows.append(
            {
                "year": yr,
                "demand_baseline_gwh": demand,
                "demand_ev_gwh": ev_demand_gwh,
                "demand_induction_gwh": induction_demand_gwh,
                "demand_total_gwh": total_demand,
            }
        )

    df = pd.DataFrame(rows)
    return EnergyProjection(yearly=df, scenario=scenario, assumptions={**base, **s})


def compute_emissions(
    demand_gwh: float,
    renewable_share: float,
    grid_emission_factor_kg_co2_per_kwh: float = 0.85,
) -> float:
    """Estimate CO2 emissions (Mt CO2eq) dari demand & renewable share.

    Grid emission factor Jawa-Bali ~0.85 kg CO2/kWh (Kemen ESDM 2022).
    """
    fossil_share = max(0.0, 1 - renewable_share)
    fossil_gwh = demand_gwh * fossil_share
    fossil_kwh = fossil_gwh * 1e6
    co2_kg = fossil_kwh * grid_emission_factor_kg_co2_per_kwh
    return co2_kg / 1e9  # Mt
