"""Deterministic cross-sector coupling for the WEF nexus.

Links computed here (before any LLM runs):
- water → food   : water stress (1 - ETa/PET) after irrigation → Doorenbos-Kassam yield
- water → energy : groundwater pumping for irrigation → extra electricity demand
- energy → water : freshwater consumed by power generation (off-site, not deducted
                   from the local balance)

All parameters come from config/nexus.yaml; values marked ASSUMPTION there are
screening defaults, not calibrated data.
"""
from __future__ import annotations

M3_PER_HA_MM = 10.0          # 1 mm of water over 1 ha = 10 m³
WATER_DENSITY_KG_M3 = 1000.0
GRAVITY_M_S2 = 9.81
J_PER_KWH = 3.6e6


def water_stress_fraction(eta_mm: float, pet_mm: float) -> float:
    """Relative evapotranspiration deficit 1 - ETa/PET, clamped to [0, 1]."""
    if pet_mm <= 0:
        return 0.0
    return max(0.0, min(1.0, 1.0 - eta_mm / pet_mm))


def stress_after_irrigation(raw_stress: float, supply_fraction: float) -> float:
    """Irrigation that delivers a fraction s of the deficit removes that share of stress.

    In the Thornthwaite-Mather balance deficit = PET - ETa, so delivering s·deficit
    raises ETa by s·deficit and the stress becomes raw_stress·(1 - s).
    """
    if not 0.0 <= supply_fraction <= 1.0:
        raise ValueError("supply_fraction must be in [0, 1]")
    return raw_stress * (1.0 - supply_fraction)


def pumping_kwh_per_m3(head_m: float, pump_efficiency: float) -> float:
    """Hydraulic lift energy E = ρ·g·H / η, in kWh per m³."""
    if head_m < 0:
        raise ValueError("head_m must be >= 0")
    if not 0.0 < pump_efficiency <= 1.0:
        raise ValueError("pump_efficiency must be in (0, 1]")
    return WATER_DENSITY_KG_M3 * GRAVITY_M_S2 * head_m / (pump_efficiency * J_PER_KWH)


def irrigation_pumping(
    *,
    deficit_mm: float,
    physical_area_ha: float,
    application_efficiency: float,
    supply_fraction: float,
    groundwater_share: float,
    head_m: float,
    pump_efficiency: float,
) -> dict:
    """Groundwater volume and electricity needed to deliver irrigation against a deficit."""
    if not 0.0 < application_efficiency <= 1.0:
        raise ValueError("application_efficiency must be in (0, 1]")
    if not 0.0 <= groundwater_share <= 1.0:
        raise ValueError("groundwater_share must be in [0, 1]")

    gross_requirement_mm = deficit_mm / application_efficiency
    delivered_mm = gross_requirement_mm * supply_fraction
    groundwater_mm = delivered_mm * groundwater_share
    groundwater_m3 = groundwater_mm * physical_area_ha * M3_PER_HA_MM
    kwh_per_m3 = pumping_kwh_per_m3(head_m, pump_efficiency)
    return {
        "gross_requirement_mm": gross_requirement_mm,
        "delivered_mm": delivered_mm,
        "groundwater_mm": groundwater_mm,
        "groundwater_volume_m3": groundwater_m3,
        "pumping_kwh_per_m3": kwh_per_m3,
        "pumping_energy_gwh": groundwater_m3 * kwh_per_m3 / 1e6,
    }


def power_sector_water_m3(
    demand_gwh: float,
    renewable_share: float,
    fossil_m3_per_mwh: float,
    renewable_m3_per_mwh: float,
) -> float:
    """Freshwater consumption of supplying `demand_gwh` at the given renewable share."""
    share = max(0.0, min(1.0, renewable_share))
    mwh = demand_gwh * 1000.0
    return mwh * ((1.0 - share) * fossil_m3_per_mwh + share * renewable_m3_per_mwh)
