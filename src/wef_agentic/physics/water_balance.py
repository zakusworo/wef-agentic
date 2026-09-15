"""Thornthwaite-Mather (1957) monthly water balance.

Soil-moisture depletion follows the original exponential retention relation

    S = C · exp(-APWL / C)

where C is the soil water capacity and APWL the accumulated potential water loss
(sum of negative P - PET since the soil was last at capacity). When no initial
storage is given, the annual cycle is repeated until end-of-year storage
converges ("spin-up"), so results do not depend on an arbitrary January state.

Reference:
- Thornthwaite, C.W. & Mather, J.R. (1957). Instructions and tables for computing
  potential evapotranspiration and the water balance.
- Cocok untuk kabupaten-scale screening; bukan substitute untuk SWAT+ di Phase 2.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd

_MIN_STORAGE_MM = 1e-9


@dataclass
class WaterBalanceResult:
    monthly: pd.DataFrame      # P, ET0, ETa, surplus, deficit, soil_moisture per bulan
    annual_summary: dict       # totals + indices (surplus, deficit, P/ET ratio)


def _apwl_from_storage(storage: float, cap: float) -> float:
    """Invert S = C·exp(-APWL/C)."""
    if storage >= cap:
        return 0.0
    return -cap * math.log(max(storage, _MIN_STORAGE_MM) / cap)


def _step(p: float, pet: float, storage: float, apwl: float, cap: float):
    """One monthly step. Returns (eta, surplus, deficit, new_storage, new_apwl)."""
    p_minus_pet = p - pet
    if p_minus_pet < 0:
        # Dry month: storage decays exponentially with accumulated potential loss
        apwl += -p_minus_pet
        target = cap * math.exp(-apwl / cap)
        withdrawal = min(max(storage - target, 0.0), -p_minus_pet)
        new_storage = storage - withdrawal
        eta = p + withdrawal
        surplus = 0.0
    else:
        # Wet month: recharge storage, excess above capacity = surplus
        new_storage = storage + p_minus_pet
        surplus = max(0.0, new_storage - cap)
        new_storage = min(new_storage, cap)
        apwl = _apwl_from_storage(new_storage, cap)
        eta = pet
    deficit = pet - eta
    return eta, surplus, deficit, new_storage, apwl


def _spin_up_storage(
    precip: list[float], pet: list[float], cap: float,
    max_cycles: int = 50, tol_mm: float = 0.01,
) -> float:
    """Repeat the annual cycle from full capacity until end-of-cycle storage converges."""
    storage = cap
    for _ in range(max_cycles):
        start = storage
        apwl = _apwl_from_storage(storage, cap)
        for p, e in zip(precip, pet, strict=True):
            _, _, _, storage, apwl = _step(p, e, storage, apwl, cap)
        if abs(storage - start) < tol_mm:
            break
    return storage


def thornthwaite_mather(
    monthly_df: pd.DataFrame,
    soil_water_capacity_mm: float = 150.0,
    initial_soil_water_mm: float | None = None,
) -> WaterBalanceResult:
    """Compute Thornthwaite-Mather monthly water balance.

    Args:
        monthly_df: DataFrame dengan kolom 'precip_mm', 'et0_mm', sorted chronologically
        soil_water_capacity_mm: kapasitas air tanah maksimum (default 150 mm untuk tanah loam)
        initial_soil_water_mm: kondisi awal; None = spun-up steady state of the given cycle

    Returns:
        WaterBalanceResult dengan monthly trace + summary annual
    """
    required_cols = {"precip_mm", "et0_mm"}
    missing = required_cols - set(monthly_df.columns)
    if missing:
        raise ValueError(f"monthly_df missing columns: {missing}")
    if soil_water_capacity_mm <= 0:
        raise ValueError("soil_water_capacity_mm must be > 0")

    df = monthly_df.copy().reset_index(drop=True)
    cap = soil_water_capacity_mm
    precip = [float(v) for v in df["precip_mm"]]
    pet = [float(v) for v in df["et0_mm"]]

    if initial_soil_water_mm is None:
        storage = _spin_up_storage(precip, pet, cap)
    else:
        storage = min(max(float(initial_soil_water_mm), 0.0), cap)
    initial_storage = storage
    apwl = _apwl_from_storage(storage, cap)

    eta_list, surplus_list, deficit_list, sm_list = [], [], [], []
    for p, e in zip(precip, pet, strict=True):
        eta, surplus, deficit, storage, apwl = _step(p, e, storage, apwl, cap)
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
    storage_change = storage - initial_storage

    summary = {
        "total_precip_mm": total_p,
        "total_pet_mm": total_pet,
        "total_eta_mm": total_eta,
        "total_surplus_mm": total_surplus,
        "total_deficit_mm": total_deficit,
        "initial_soil_water_mm": initial_storage,
        "storage_change_mm": storage_change,
        # P = ETa + surplus + ΔS must close; non-zero residual means a model bug
        "mass_balance_residual_mm": total_p - total_eta - total_surplus - storage_change,
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
        et0_temp_sensitivity: fraksi per °C — default 0.04 (≈4%/°C, Allen 1998 approximate)

    Returns:
        DataFrame baru dengan kolom precip & et0 di-adjust
    """
    df = monthly_df.copy()
    df["precip_mm"] = df["precip_mm"] * (1 + delta_precip_pct / 100)
    df["et0_mm"] = df["et0_mm"] * (1 + et0_temp_sensitivity * delta_temp_c)
    return df
