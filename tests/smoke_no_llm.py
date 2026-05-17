"""Smoke test — verify imports, tool dispatch, scenarios. No LLM call."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def test_imports():
    from wef_agentic.agents import (
        CoordinatorAgent,
        CriticAgent,
        EnergyAgent,
        FoodAgent,
        WaterAgent,
    )
    from wef_agentic.geo import resolve_location, list_presets
    from wef_agentic.llm.footprint import NexusFootprint
    from wef_agentic.llm.provider import get_provider_for_agent
    from wef_agentic.orchestration import SCENARIOS, get_scenario
    from wef_agentic.tools import call_tool, list_tool_names

    print("✓ Imports OK")
    print(f"  Agents: 5")
    print(f"  Tools registered: {len(list_tool_names())} ({', '.join(list_tool_names())})")
    print(f"  Scenarios: {len(SCENARIOS)} ({', '.join(SCENARIOS.keys())})")
    print(f"  Presets: {[p.name for p in list_presets()]}")


def test_tools_sleman():
    from wef_agentic.tools import call_tool

    history = call_tool("get_electricity_history", location_query="sleman")
    assert "data" in history
    print(f"✓ get_electricity_history (Sleman): {len(history['data'])} years")

    food_history = call_tool("get_food_history", location_query="sleman")
    assert "rice_harvest_area_ha" in food_history
    print(f"✓ get_food_history (Sleman): {len(food_history['rice_harvest_area_ha'])} years")

    proj = call_tool("project_energy_demand", location_query="sleman",
                     scenario="BAU", horizon=2050)
    assert proj["endpoints"]["demand_2050_gwh"] is not None
    print(f"✓ project_energy_demand (Sleman 2050): {proj['endpoints']['demand_2050_gwh']:.1f} GWh "
          f"[{proj['data_quality']}]")

    yield_proj = call_tool(
        "project_crop_yield",
        location_query="sleman",
        crop="padi",
        scenario="BAU",
        water_stress_fraction=0.1,
        lp2b_protection="moderate",
        horizon=2050,
    )
    assert yield_proj["endpoints"]["production_2050_t"] is not None
    print(f"✓ project_crop_yield (Sleman 2050): {yield_proj['endpoints']['production_2050_t']:.0f} ton")

    ssl = call_tool("compute_food_ssl", production_t=200000, location_query="sleman", year=2030)
    print(f"✓ compute_food_ssl: SSL={ssl['ssl']:.2f} ({ssl['interpretation']})")

    em = call_tool("estimate_emissions", demand_gwh=2000, renewable_share=0.34, country_code="ID")
    print(f"✓ estimate_emissions (Indonesia): {em['co2_emissions_mt']} Mt CO2 "
          f"(grid factor {em['grid_emission_factor_kg_co2_per_kwh']})")


def test_physics_unit():
    import pandas as pd
    from wef_agentic.physics.water_balance import thornthwaite_mather

    df = pd.DataFrame(
        {
            "precip_mm": [350, 280, 200, 100, 80, 50, 40, 60, 100, 200, 300, 350],
            "et0_mm": [110, 100, 120, 130, 140, 145, 150, 145, 130, 120, 110, 105],
        }
    )
    result = thornthwaite_mather(df)
    assert result.annual_summary["total_precip_mm"] > 0
    print(f"✓ thornthwaite_mather: surplus={result.annual_summary['total_surplus_mm']:.0f}mm, "
          f"deficit={result.annual_summary['total_deficit_mm']:.0f}mm")


def test_scenarios():
    from wef_agentic.orchestration import list_scenarios, get_scenario

    scenarios = list_scenarios()
    assert len(scenarios) == 5
    for s in scenarios:
        assert "name" in s and "location_query" in s
    print(f"✓ Scenarios: {[s['name'] for s in scenarios]}")

    # Test location override
    sc = get_scenario("S1_BAU_2030", location_query="Bandung")
    assert sc["location_query"] == "Bandung"
    print(f"✓ Scenario location override works: Bandung")


def test_geo():
    from wef_agentic.geo import resolve_location, get_preset

    # Preset (no network)
    sleman = get_preset("sleman")
    assert sleman is not None and sleman.is_indonesia
    print(f"✓ Preset Sleman: {sleman.display}")


def test_footprint():
    from wef_agentic.llm.footprint import FootprintEntry, NexusFootprint

    fp = NexusFootprint()
    fp.add(FootprintEntry(agent="water", provider="ollama-local", model="gemma4:e4b",
                          input_tokens=1500, output_tokens=500))
    fp.add(FootprintEntry(agent="energy", provider="ollama-local", model="gemma4:e4b",
                          input_tokens=2000, output_tokens=800))
    est = fp.estimate()
    assert est["total_tokens"] == 4800
    print(f"✓ NexusFootprint: tokens={est['total_tokens']}, "
          f"kWh={est['energy_kwh']:.4f}, water_L={est['water_l']:.4f}, "
          f"CO2_kg={est['co2_kg']:.4f}")


if __name__ == "__main__":
    print("=" * 60)
    print("WEF-Agentic smoke test (no LLM)")
    print("=" * 60)
    test_imports()
    print()
    test_geo()
    print()
    test_physics_unit()
    print()
    test_tools_sleman()
    print()
    test_scenarios()
    print()
    test_footprint()
    print()
    print("=" * 60)
    print("All non-LLM tests passed ✓")
    print("=" * 60)
