"""Open-Meteo Historical API — free, no key. Location-agnostic.

Docs: https://open-meteo.com/en/docs/historical-weather-api
"""
from __future__ import annotations

import httpx
import pandas as pd
from tenacity import retry, stop_after_attempt, wait_exponential

from wef_agentic.config.settings import PROCESSED_DIR
from wef_agentic.geo.location import Location
from wef_agentic.geo.presets import SLEMAN

OPENMETEO_URL = "https://archive-api.open-meteo.com/v1/archive"

DAILY_VARS = [
    "temperature_2m_max",
    "temperature_2m_min",
    "temperature_2m_mean",
    "precipitation_sum",
    "relative_humidity_2m_mean",
    "wind_speed_10m_max",
    "shortwave_radiation_sum",
    "et0_fao_evapotranspiration",
]

DEFAULT_START = "1991-01-01"
DEFAULT_END = "2024-12-31"


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def fetch_openmeteo_point(
    lat: float,
    lon: float,
    start: str = DEFAULT_START,
    end: str = DEFAULT_END,
    timezone: str = "Asia/Jakarta",
) -> pd.DataFrame:
    """Fetch daily historical weather untuk 1 titik."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start,
        "end_date": end,
        "daily": ",".join(DAILY_VARS),
        "timezone": timezone,
    }
    with httpx.Client(timeout=120) as client:
        r = client.get(OPENMETEO_URL, params=params)
        r.raise_for_status()
        data = r.json()

    daily = data.get("daily", {})
    df = pd.DataFrame(daily)
    df["date"] = pd.to_datetime(df["time"])
    df = df.drop(columns=["time"])
    df.insert(0, "lat", lat)
    df.insert(1, "lon", lon)
    return df


def fetch_climate_for_location(
    location: Location,
    start: str = DEFAULT_START,
    end: str = DEFAULT_END,
    cache: bool = True,
) -> pd.DataFrame:
    """Universal climate fetcher untuk Location apapun.

    - Sleman preset: pakai 3 stasiun + fixture cache jika tersedia
    - Other location: single point fetch live
    """
    if location.name == "Sleman" and location.source == "preset":
        return _fetch_sleman_stations(start, end, cache)

    cache_path = PROCESSED_DIR / f"openmeteo_{location.slug}_{start}_{end}.parquet"
    if cache and cache_path.exists():
        return pd.read_parquet(cache_path)

    df = fetch_openmeteo_point(
        location.lat, location.lon, start=start, end=end, timezone=location.timezone
    )
    df["station"] = location.name
    df["zone"] = f"{location.country} (single point)"

    if cache:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(cache_path, index=False)
    return df


def _fetch_sleman_stations(
    start: str = DEFAULT_START,
    end: str = DEFAULT_END,
    cache: bool = True,
) -> pd.DataFrame:
    """Sleman-specific: 3 stations fetcher (legacy / fixture-cached)."""
    cache_path = PROCESSED_DIR / f"openmeteo_sleman_{start}_{end}.parquet"
    if cache and cache_path.exists():
        return pd.read_parquet(cache_path)

    stations = SLEMAN.metadata.get("stations", [])
    if not stations:
        df = fetch_openmeteo_point(
            SLEMAN.lat, SLEMAN.lon, start=start, end=end, timezone=SLEMAN.timezone
        )
        df["station"] = "Sleman"
        df["zone"] = "Sleman centroid"
    else:
        frames = []
        for st in stations:
            df_st = fetch_openmeteo_point(
                st["lat"], st["lon"], start=start, end=end, timezone=SLEMAN.timezone
            )
            df_st["station"] = st["name"]
            df_st["zone"] = st["zone"]
            frames.append(df_st)
        df = pd.concat(frames, ignore_index=True)

    if cache:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(cache_path, index=False)
    return df


def aggregate_monthly(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    agg_map = {
        "temperature_2m_max": "mean",
        "temperature_2m_min": "mean",
        "temperature_2m_mean": "mean",
        "precipitation_sum": "sum",
        "relative_humidity_2m_mean": "mean",
        "wind_speed_10m_max": "mean",
        "shortwave_radiation_sum": "sum",
        "et0_fao_evapotranspiration": "sum",
    }
    monthly = (
        df.groupby(["station", "zone", "year", "month"], as_index=False)
        .agg(agg_map)
        .rename(
            columns={
                "precipitation_sum": "precip_mm",
                "temperature_2m_mean": "tmean_c",
                "et0_fao_evapotranspiration": "et0_mm",
                "shortwave_radiation_sum": "srad_mj_m2",
            }
        )
    )
    return monthly


def annual_summary(df_monthly: pd.DataFrame) -> pd.DataFrame:
    return (
        df_monthly.groupby(["station", "zone", "year"], as_index=False)
        .agg(
            precip_mm=("precip_mm", "sum"),
            tmean_c=("tmean_c", "mean"),
            et0_mm=("et0_mm", "sum"),
        )
    )


def fetch_sleman_stations(
    start: str = DEFAULT_START,
    end: str = DEFAULT_END,
    cache: bool = True,
) -> pd.DataFrame:
    """Deprecated alias — use fetch_climate_for_location(SLEMAN)."""
    return _fetch_sleman_stations(start, end, cache)
