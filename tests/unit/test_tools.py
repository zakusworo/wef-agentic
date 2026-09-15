import json

from tests.conftest import BANDUNG
from wef_agentic.data.sources import WorldBankSource
from wef_agentic.geo import Location, remember_location
from wef_agentic.tools import call_tool


def test_sleman_crop_projection_is_bps_anchored():
    out = call_tool("project_crop_yield", location_query="sleman", water_stress_fraction=0.05, horizon=2030)
    assert out["available"] is True
    assert out["assumptions"]["base_area_ha"] == 39000
    assert {p["source"] for p in out["provenance"]} == {"bps-sleman-static"}


def test_other_city_does_not_borrow_sleman_farmland():
    remember_location("bandung", BANDUNG)
    out = call_tool("project_crop_yield", location_query="bandung", water_stress_fraction=0.05)
    assert out["available"] is False
    assert "override_" in out["reason"]


def test_manual_override_enables_local_food_projection(external_dir):
    remember_location("bandung", BANDUNG)
    payload = {"version": "1.0", "variables": {
        "food.rice_area_ha": {"value": 1200, "year": 2024, "source": "Distan Kota Bandung"},
    }}
    path = external_dir / f"override_{BANDUNG.slug}.json"
    path.write_text(json.dumps(payload))
    try:
        out = call_tool("project_crop_yield", location_query="bandung", horizon=2030)
    finally:
        path.unlink()
    assert out["available"] is True
    assert out["assumptions"]["base_area_ha"] == 1200
    assert out["assumptions"]["base_year"] == 2024
    assert out["warnings"]  # land-loss rate unknown → explicit warning


def test_unknown_population_is_flagged_not_silent():
    remember_location("nowhere", Location(name="Nowhere", lat=0, lon=0, country_code="ID", source="geocoded"))
    out = call_tool("get_electricity_history", location_query="nowhere")
    pop = next(p for p in out["provenance"] if p["variable"] == "socio.population")
    assert pop["source"] == "fallback-constant"
    assert pop["confidence"] < 0.2


def test_geocoded_population_preferred_and_worldbank_never_serves_population():
    assert "socio.population" not in WorldBankSource.supported_variables
    remember_location("bandung", BANDUNG)
    out = call_tool("get_electricity_history", location_query="bandung")
    pop = next(p for p in out["provenance"] if p["variable"] == "socio.population")
    assert pop["source"] == "geocoding-gazetteer"
    assert out["population"] == BANDUNG.population
