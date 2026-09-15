"""Shared fixtures: offline data (synthetic Sleman fixture, no network) and a fake LLM."""
from __future__ import annotations

import pytest

from wef_agentic.data.constants import DEFAULT_END, DEFAULT_START
from wef_agentic.data.fixture import synth_daily, write_sleman_fixture
from wef_agentic.data.sources import DataSourceUnavailable
from wef_agentic.geo import Location, clear_location_cache
from wef_agentic.llm.provider import LLMProvider
from wef_agentic.llm.types import LLMResponse, Usage


class FakeProvider(LLMProvider):
    """Scripted provider. `replies` items: "text" or ("text", done_reason)."""

    def __init__(self, replies=None, model="fake-model", name="ollama-cloud", max_tokens=1000):
        super().__init__(model=model, max_tokens=max_tokens)
        self.name = name
        self.replies = list(replies or [])
        self.calls: list[dict] = []

    async def chat(self, messages, tools=None):
        self.calls.append({"messages": messages, "max_tokens": self.max_tokens})
        reply = self.replies.pop(0) if self.replies else "Analisis uji. Caveat: advisory only."
        content, done_reason = reply if isinstance(reply, tuple) else (reply, "stop")
        return LLMResponse(
            content=content, usage=Usage(input_tokens=10, output_tokens=5),
            provider=self.name, model=self.model, done_reason=done_reason,
        )


BANDUNG = Location(
    name="Bandung", lat=-6.921, lon=107.607, country="Indonesia", country_code="ID",
    admin1="West Java", population=1_699_719, timezone="Asia/Jakarta", source="geocoded",
)


@pytest.fixture(scope="session")
def data_dirs(tmp_path_factory):
    import numpy as np

    root = tmp_path_factory.mktemp("wef-data")
    processed = root / "processed"
    write_sleman_fixture(processed)
    # Climate cache for a non-preset city, in the format fetch_climate_for_location reads
    bandung = synth_daily(BANDUNG.lat, BANDUNG.lon, BANDUNG.name, "Indonesia (single point)",
                          np.random.default_rng(7))
    bandung.to_parquet(processed / f"openmeteo_{BANDUNG.slug}_{DEFAULT_START}_{DEFAULT_END}.parquet",
                       index=False)
    external = root / "external"
    external.mkdir()
    return processed, external


@pytest.fixture(autouse=True)
def offline(data_dirs, monkeypatch):
    processed, external = data_dirs

    def no_network(*_args, **_kwargs):
        raise AssertionError("network access attempted in tests")

    def worldbank_offline(self, country_code, indicator):
        raise DataSourceUnavailable("offline test")

    monkeypatch.setattr("wef_agentic.data.openmeteo.PROCESSED_DIR", processed)
    monkeypatch.setattr("wef_agentic.data.sources.manual_source.EXTERNAL_DIR", external)
    monkeypatch.setattr("wef_agentic.data.openmeteo.fetch_openmeteo_point", no_network)
    monkeypatch.setattr("wef_agentic.geo.geocode_first", no_network)
    monkeypatch.setattr(
        "wef_agentic.data.sources.worldbank_source.WorldBankSource._fetch_indicator", worldbank_offline
    )
    monkeypatch.delenv("WEF_AGENTIC_PROVIDER_OVERRIDE", raising=False)
    monkeypatch.delenv("WEF_AGENTIC_MODEL_OVERRIDE", raising=False)
    clear_location_cache()
    yield
    clear_location_cache()


@pytest.fixture
def external_dir(data_dirs):
    return data_dirs[1]


@pytest.fixture
def fake_providers(monkeypatch):
    """Route every agent to a FakeProvider; returns the dict to script/inspect them."""
    providers: dict[str, FakeProvider] = {}

    def factory(agent_name):
        return providers.setdefault(agent_name, FakeProvider())

    monkeypatch.setattr("wef_agentic.agents.base.get_provider_for_agent", factory)
    return providers
