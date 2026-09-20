import pandas as pd
import pytest

from wef_agentic.data.openmeteo import fetch_openmeteo_point


def test_multiyear_download_has_nonoverlapping_calendar_chunks(monkeypatch):
    calls = []
    pauses = []

    def chunk(lat, lon, start, end, timezone):
        calls.append((start, end))
        return pd.DataFrame({"date": pd.date_range(start, end)})

    monkeypatch.setattr("wef_agentic.data.openmeteo._fetch_openmeteo_chunk", chunk)
    monkeypatch.setattr("wef_agentic.data.openmeteo.time.sleep", pauses.append)
    data = fetch_openmeteo_point(0, 0, "2019-12-31", "2021-01-01")
    assert calls == [("2019-12-31", "2019-12-31"), ("2020-01-01", "2020-12-31"),
                     ("2021-01-01", "2021-01-01")]
    assert len(data) == 368
    assert data.date.is_unique
    assert pauses == [3, 3, 3]


def test_reversed_download_dates_fail_before_network():
    with pytest.raises(ValueError, match="start"):
        fetch_openmeteo_point(0, 0, "2024-01-02", "2024-01-01")
