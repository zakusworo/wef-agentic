import math

import numpy as np
import pandas as pd
import pytest

from wef_agentic.physics.water_balance import (
    irrigation_demand_mm,
    scenario_apply_climate_change,
    thornthwaite_mather,
)

MONSOON = pd.DataFrame({
    "precip_mm": [350, 280, 200, 100, 80, 50, 40, 60, 100, 200, 300, 350],
    "et0_mm": [110, 100, 120, 130, 140, 145, 150, 145, 130, 120, 110, 105],
})


def test_mass_balance_closes():
    s = thornthwaite_mather(MONSOON).annual_summary
    assert s["mass_balance_residual_mm"] == pytest.approx(0.0, abs=1e-9)
    assert s["total_precip_mm"] == pytest.approx(
        s["total_eta_mm"] + s["total_surplus_mm"] + s["storage_change_mm"]
    )


def test_deficit_is_pet_minus_eta():
    m = thornthwaite_mather(MONSOON).monthly
    assert np.allclose(m["deficit_mm"], m["et0_mm"] - m["eta_mm"])
    assert (m["eta_mm"] <= m["et0_mm"] + 1e-9).all()


def test_dry_months_follow_exponential_retention_not_linear_depletion():
    dry = pd.DataFrame({"precip_mm": [0.0, 0.0, 0.0], "et0_mm": [50.0, 50.0, 50.0]})
    m = thornthwaite_mather(dry, soil_water_capacity_mm=150, initial_soil_water_mm=150).monthly
    expected = [150 * math.exp(-apwl / 150) for apwl in (50, 100, 150)]
    assert np.allclose(m["soil_moisture_mm"], expected)
    # linear depletion would have emptied the soil after 150 mm of loss
    assert m["soil_moisture_mm"].iloc[-1] > 50


def test_default_initial_storage_is_periodic_steady_state():
    s = thornthwaite_mather(MONSOON).annual_summary
    assert s["storage_change_mm"] == pytest.approx(0.0, abs=0.05)


def test_explicit_initial_storage_changes_result():
    empty_start = thornthwaite_mather(MONSOON, initial_soil_water_mm=0).annual_summary
    spun_up = thornthwaite_mather(MONSOON).annual_summary
    assert empty_start["total_surplus_mm"] < spun_up["total_surplus_mm"]


def test_missing_columns_raise():
    with pytest.raises(ValueError, match="missing columns"):
        thornthwaite_mather(pd.DataFrame({"precip_mm": [1.0]}))


def test_irrigation_demand():
    assert irrigation_demand_mm(65, 0.65) == pytest.approx(100)
    with pytest.raises(ValueError):
        irrigation_demand_mm(10, 0)


def test_climate_delta():
    out = scenario_apply_climate_change(MONSOON, delta_precip_pct=-10, delta_temp_c=1.0)
    assert np.allclose(out["precip_mm"], MONSOON["precip_mm"] * 0.9)
    assert np.allclose(out["et0_mm"], MONSOON["et0_mm"] * 1.04)
