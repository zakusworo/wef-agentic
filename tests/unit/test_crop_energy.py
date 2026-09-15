import pytest

from wef_agentic.physics.crop_yield import compute_ssl, project_yield, yield_ratio
from wef_agentic.physics.energy_demand import compute_emissions, project_demand


def test_yield_ratio_is_clamped():
    assert yield_ratio(1.0, 1.0) == 1.0
    assert yield_ratio(0.0, 1.0) == 0.0
    assert yield_ratio(0.9, 1.0, crop="padi") == pytest.approx(1 - 1.1 * 0.1)


def test_projection_uses_supplied_area_not_a_default_region():
    p = project_yield(base_area_ha=1000, annual_loss_ha=10, horizon=2025, base_year=2023)
    assert p.yearly["area_ha"].tolist() == [1000, 990, 980]


def test_lp2b_protection_scales_land_loss():
    strict = project_yield(base_area_ha=1000, annual_loss_ha=10, lp2b_protection="strict")
    lax = project_yield(base_area_ha=1000, annual_loss_ha=10, lp2b_protection="lax")
    assert strict.assumptions["annual_loss_ha"] == pytest.approx(3)
    assert lax.assumptions["annual_loss_ha"] == pytest.approx(18)


def test_water_stress_reduces_yield():
    p = project_yield(base_area_ha=100, annual_loss_ha=0, water_stress_fraction=0.1, horizon=2023)
    assert p.yearly["yield_t_ha"].iloc[0] == pytest.approx(7.0 * (1 - 1.1 * 0.1))


def test_ssl():
    assert compute_ssl(115, 1000, per_capita_demand_kg=115) == pytest.approx(1.0)
    assert compute_ssl(10, 0) == 0.0


def test_demand_starts_at_base_and_ramps_extra_to_horizon():
    y = project_demand("BAU", horizon=2030, extra_demand_at_horizon_gwh=7.0).yearly.set_index("year")
    assert y.loc[2023, "demand_total_gwh"] == pytest.approx(1880)
    assert y.loc[2023, "demand_irrigation_pumping_gwh"] == 0
    assert y.loc[2027, "demand_irrigation_pumping_gwh"] == pytest.approx(4.0)
    assert y.loc[2030, "demand_irrigation_pumping_gwh"] == pytest.approx(7.0)


def test_unknown_energy_scenario():
    with pytest.raises(ValueError):
        project_demand("nope")


def test_emissions():
    assert compute_emissions(1000, 0.5, 0.8) == pytest.approx(0.4)
