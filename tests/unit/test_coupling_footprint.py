import pytest

from wef_agentic.llm.footprint import FootprintEntry, NexusFootprint, model_size_class
from wef_agentic.physics.coupling import (
    irrigation_pumping,
    power_sector_water_m3,
    pumping_kwh_per_m3,
    stress_after_irrigation,
    water_stress_fraction,
)


def test_water_stress_fraction():
    assert water_stress_fraction(90, 100) == pytest.approx(0.1)
    assert water_stress_fraction(120, 100) == 0.0
    assert water_stress_fraction(10, 0) == 0.0


def test_stress_after_irrigation():
    assert stress_after_irrigation(0.2, 0.6) == pytest.approx(0.08)
    with pytest.raises(ValueError):
        stress_after_irrigation(0.2, 1.5)


def test_pumping_energy_is_hydraulic_lift():
    # E = rho * g * H / eta = 1000 * 9.81 * 30 / 0.45 J per m3
    assert pumping_kwh_per_m3(30, 0.45) == pytest.approx(1000 * 9.81 * 30 / 0.45 / 3.6e6)


def test_irrigation_pumping_volumes():
    out = irrigation_pumping(
        deficit_mm=65, physical_area_ha=100, application_efficiency=0.65,
        supply_fraction=0.5, groundwater_share=0.2, head_m=30, pump_efficiency=0.45,
    )
    assert out["gross_requirement_mm"] == pytest.approx(100)
    assert out["groundwater_mm"] == pytest.approx(10)
    assert out["groundwater_volume_m3"] == pytest.approx(10 * 100 * 10)
    assert out["pumping_energy_gwh"] == pytest.approx(10_000 * pumping_kwh_per_m3(30, 0.45) / 1e6)


def test_power_sector_water():
    assert power_sector_water_m3(1, 0.25, 2.6, 0.1) == pytest.approx(1000 * (0.75 * 2.6 + 0.25 * 0.1))


CFG = {
    "kwh_per_1k_output_tokens": 0.0003,
    "input_token_weight": 0.1,
    "size_multiplier": {"small": 0.1, "medium": 1.0, "large": 3.0},
    "size_patterns": [{"pattern": "tiny", "size": "small"}],
    "providers": {
        "cloud": {"pue": 1.2, "wue_onsite_l_per_kwh": 0.55, "ewif_l_per_kwh": 3.14, "co2_kg_per_kwh": 0.4},
        "local": {"pue": 1.0, "wue_onsite_l_per_kwh": 0.0, "ewif_l_per_kwh": None, "co2_kg_per_kwh": 0.85},
    },
}


def test_footprint_applies_provider_factors():
    fp = NexusFootprint([FootprintEntry("water", "cloud", "big-model", 1000, 1000)])
    est = fp.estimate(CFG)
    it_kwh = (1000 + 0.1 * 1000) / 1000 * 0.0003
    assert est["energy_kwh"] == pytest.approx(it_kwh * 1.2)
    assert est["water_onsite_l"] == pytest.approx(it_kwh * 0.55)
    assert est["water_offsite_l"] == pytest.approx(it_kwh * 1.2 * 3.14)
    assert est["co2_kg"] == pytest.approx(it_kwh * 1.2 * 0.4)
    assert est["notes"] == []


def test_small_model_and_unknown_offsite_water_are_reported():
    fp = NexusFootprint([FootprintEntry("water", "local", "tiny", 0, 1000)])
    est = fp.estimate(CFG)
    assert est["per_entry"][0]["size_class"] == "small"
    assert est["energy_kwh"] == pytest.approx(0.0003 * 0.1)
    assert est["per_entry"][0]["water_offsite_l"] is None
    assert est["notes"] and "local" in est["notes"][0]


@pytest.mark.parametrize(("model", "size"), [
    ("gemma4:e4b", "small"), ("llama3.2:1b", "small"), ("qwen3:32b", "medium"),
    ("claude-sonnet-4-6", "medium"), ("glm-5.3-flash:cloud", "medium"),
    ("kimi-k2.6:cloud", "large"), ("deepseek-v4-pro:cloud", "large"),
])
def test_repo_config_size_classes(model, size):
    assert model_size_class(model) == size
