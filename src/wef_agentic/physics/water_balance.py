"""Thornthwaite-Mather monthly water balance — simplified.

Reference:
- Thornthwaite, C.W. & Mather, J.R. (1957). Instructions and tables for computing
  potential evapotranspiration and the water balance.
- Cocok untuk kabupaten-scale screening; bukan substitute untuk SWAT+ di Phase 2.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class WaterBalanceResult:
    monthly: pd.DataFrame      # P, ET0, ETa, surplus, deficit, soil_moisture per bulan
    annual_summary: dict       # totals + indices (surplus, deficit, P/ET ratio)


def thornthwaite_mather(
    monthly_df: pd.DataFrame,
    soil_water_capacity_mm: float = 150.0,
    initial_soil_water_mm: float | None = None,
) -> WaterBalanceResult:
    """Compute Thornthwaite-Mather monthly water balance.

    Args:
        monthly_df: DataFrame dengan kolom 'precip_mm', 'et0_mm', sorted chronologically
        soil_water_capacity_mm: kapasitas air tanah maksimum (default 150 mm untuk tanah loam)
        initial_soil_water_mm: kondisi awal (default = full capacity)

    Returns:
        WaterBalanceResult dengan monthly trace + summary annual
    """
    required_cols = {"precip_mm", "et0_mm"}
    missing = required_cols - set(monthly_df.columns)
    if missing:
        raise ValueError(f"monthly_df missing columns: {missing}")

    df = monthly_df.copy().reset_index(drop=True)
    n = len(df)

    storage = soil_water_capacity_mm if initial_soil_water_mm is None else initial_soil_water_mm
    cap = soil_water_capacity_mm

    eta_list, surplus_list, deficit_list, sm_list = [], [], [], []

    for i in range(n):
        p = float(df.loc[i, "precip_mm"])
        pet = float(df.loc[i, "et0_mm"])

        # Step 1: net P - PET
        p_minus_pet = p - pet

        if p_minus_pet >= 0:
            # Wet month: storage naik, kelebihan = surplus
            new_storage = storage + p_minus_pet
            if new_storage > cap:
                surplus = new_storage - cap
                new_storage = cap
            else:
                surplus = 0.0
            eta = pet  # ET actual = ET potential di bulan basah
            deficit = 0.0
        else:
            # Dry month: tarik dari storage
            # Thornthwaite-Mather menggunakan eksponensial decay
            # APWL (Accumulated Potential Water Loss) = sum negative P-PET sejak storage penuh
            # Simplification: linear depletion
            withdrawal = min(storage, abs(p_minus_pet))
            new_storage = storage - withdrawal
            eta = p + withdrawal  # ET actual = P + air dari storage
            deficit = max(0.0, pet - eta)
            surplus = 0.0

        storage = new_storage
        eta_list.append(eta)
        surplus_list.append(surplus)
        deficit_list.append(deficit)
        sm_list.append(storage)

    df["eta_mm"] = eta_list
    df["surplus_mm"] = surplus_list
    df["deficit_mm"] = deficit_list
    df["soil_moisture_mm"] = sm_list

    total_p = float(df["precip_mm"].sum())
    total_pet = float(df["et0_mm"].sum())
    total_eta = float(df["eta_mm"].sum())
    total_surplus = float(df["surplus_mm"].sum())
    total_deficit = float(df["deficit_mm"].sum())

    summary = {
        "total_precip_mm": total_p,
        "total_pet_mm": total_pet,
        "total_eta_mm": total_eta,
        "total_surplus_mm": total_surplus,
        "total_deficit_mm": total_deficit,
        "p_pet_ratio": (total_p / total_pet) if total_pet > 0 else float("nan"),
        "aridity_index": (total_pet / total_p) if total_p > 0 else float("inf"),
    }

    return WaterBalanceResult(monthly=df, annual_summary=summary)


def irrigation_demand_mm(deficit_mm: float, application_efficiency: float = 0.65) -> float:
    """Convert moisture deficit ke demand air irigasi (mm) di lahan.

    Default efisiensi aplikasi irigasi 65% (irigasi gravitasi Indonesia).
    """
    if application_efficiency <= 0 or application_efficiency > 1:
        raise ValueError("application_efficiency must be in (0, 1]")
    return deficit_mm / application_efficiency


def scenario_apply_climate_change(
    monthly_df: pd.DataFrame,
    delta_precip_pct: float = 0.0,
    delta_temp_c: float = 0.0,
    et0_temp_sensitivity: float = 0.04,
) -> pd.DataFrame:
    """Apply delta-change scenario ke baseline monthly data.

    Args:
        monthly_df: baseline dengan precip_mm, et0_mm
        delta_precip_pct: persen perubahan hujan (e.g. -10.0 = turun 10%)
        delta_temp_c: kenaikan suhu (°C). Translate ke ET0 via sensitivity factor.
        et0_temp_sensitivity: %/°C — default 4%/°C (Allen 1998 approximate)

    Returns:
        DataFrame baru dengan kolom precip & et0 di-adjust
    """
    df = monthly_df.copy()
    df["precip_mm"] = df["precip_mm"] * (1 + delta_precip_pct / 100)
    df["et0_mm"] = df["et0_mm"] * (1 + et0_temp_sensitivity * delta_temp_c)
    return df
