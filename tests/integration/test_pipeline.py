import json

import pytest

from tests.conftest import BANDUNG, FakeProvider
from wef_agentic.llm.types import EmptyCompletionError
from wef_agentic.orchestration import build_run_record, compute_nexus, get_scenario, run_scenario
from wef_agentic.reporting import generate_scenario_report
from wef_agentic.reporting.charts import build_all_charts


def test_water_stress_is_derived_from_climate_not_a_scenario_constant():
    wet = compute_nexus(get_scenario("S3_NetZero_2045"))
    dry = compute_nexus(get_scenario("S4_Climate_Stress"))
    for n in (wet, dry):
        assert n.crop_projection["water_stress_fraction"] == n.coupling["water_stress_effective"]
    assert dry.coupling["water_stress_raw"] > wet.coupling["water_stress_raw"]
    assert dry.coupling["extra_pumping_demand_gwh"] > wet.coupling["extra_pumping_demand_gwh"] > 0
    pumping = dry.energy_projection["endpoints"]["irrigation_pumping_horizon_gwh"]
    assert pumping == pytest.approx(dry.coupling["extra_pumping_demand_gwh"])


def test_sleman_checks_pass_hard_consistency():
    n = compute_nexus(get_scenario("S2_JETP_Aligned"))
    status = {c["name"]: c["status"] for c in n.checks}
    assert status["water_mass_balance"] == "ok"
    assert status["population_consistency"] == "ok"
    assert "fail" not in status.values()


def test_water_stress_override_is_honoured_with_warning():
    sc = get_scenario("S1_BAU_2030")
    sc["water_stress_override"] = 0.3
    n = compute_nexus(sc)
    assert n.crop_projection["water_stress_fraction"] == 0.3
    assert any("override" in w for w in n.warnings)


async def test_full_pipeline_sleman(fake_providers):
    events = []
    result = await run_scenario(get_scenario("S2_JETP_Aligned"),
                                on_event=lambda phase, _payload: events.append(phase))

    assert events[0] == "nexus_start" and events[-1] == "done"
    critic_prompt = fake_providers["critic"].calls[0]["messages"][1].content
    assert "Angka Kunci" in critic_prompt
    assert "water_mass_balance" in critic_prompt
    coordinator_prompt = fake_providers["coordinator"].calls[0]["messages"][1].content
    assert "Sleman" in coordinator_prompt

    record = build_run_record(result)
    json.dumps(record)
    assert [a["name"] for a in record["agents"]] == ["water", "energy", "food", "critic", "coordinator"]
    assert all(a["prompt_sha256"] and a["content"] for a in record["agents"])
    assert record["footprint"]["total_tokens"] == 5 * 15

    assert generate_scenario_report(result).startswith(b"%PDF")
    assert build_all_charts(result)["water"] is not None


async def test_custom_city_runs_without_sleman_context(fake_providers):
    scenario = get_scenario("S1_BAU_2030", location_query="Bandung")
    result = await run_scenario(scenario, location=BANDUNG)

    assert result.nexus.location["name"] == "Bandung"
    assert result.nexus.food_available is False
    assert result.nexus.food_ssl is None
    assert result.nexus.coupling["extra_pumping_demand_gwh"] == 0.0
    assert any("irigasi" in w for w in result.nexus.warnings)
    coordinator_prompt = fake_providers["coordinator"].calls[0]["messages"][1].content
    assert "Sleman" not in coordinator_prompt
    assert generate_scenario_report(result).startswith(b"%PDF")


async def test_empty_critic_fails_the_run(monkeypatch):
    providers = {"critic": FakeProvider(replies=[("", "length"), ("", "length")])}
    monkeypatch.setattr("wef_agentic.agents.base.get_provider_for_agent",
                        lambda name: providers.setdefault(name, FakeProvider()))
    with pytest.raises(EmptyCompletionError):
        await run_scenario(get_scenario("S1_BAU_2030"))
    assert "coordinator" not in [c for c in providers if providers[c].calls]
