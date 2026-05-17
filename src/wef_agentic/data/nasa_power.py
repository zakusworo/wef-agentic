"""NASA POWER API — free, no key. Location-agnostic.

Docs: https://power.larc.nasa.gov/docs/services/api/temporal/daily/
"""
from __future__ import annotations

import httpx
import pandas as pd
from tenacity import retry, stop_after_attempt, wait_exponential

from wef_agentic.config.settings import PROCESSED_DIR
from wef_agentic.geo.location import Location

NASA_POWER_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"

VARS = ["ALLSKY_SFC_SW_DWN", "WS2M", "T2M", "PRECTOTCORR"]


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def fetch_nasa_power(
    lat: float,
    lon: float,
    start: str = "19910101",
    end: str = "20241231",
) -> pd.DataFrame:
    """Fetch NASA POWER daily data untuk 1 titik."""
    params = {
        "parameters": ",".join(VARS),
        "community": "AG",
        "longitude": lon,
        "latitude": lat,
        "start": start,
        "end": end,
        "format": "JSON",
    }
    with httpx.Client(timeout=120) as client:
        r = client.get(NASA_POWER_URL, params=params)
        r.raise_for_status()
        data = r.json()

    props = data.get("properties", {}).get("parameter", {})
    if not props:
        raise ValueError("NASA POWER returned empty data")

    var_dfs = []
    for var, daily in props.items():
        var_df = pd.DataFrame.from_dict(daily, orient="index", columns=[var])
        var_dfs.append(var_df)

    df = pd.concat(var_dfs, axis=1)
    df.index = pd.to_datetime(df.index, format="%Y%m%d")
    df.index.name = "date"
    df = df.reset_index()
    df.insert(1, "lat", lat)
    df.insert(2, "lon", lon)
    return df


def fetch_for_location(location: Location, cache: bool = True) -> pd.DataFrame:
    """Universal NASA POWER fetcher untuk Location apapun."""
    cache_path = PROCESSED_DIR / f"nasa_power_{location.slug}.parquet"
    if cache and cache_path.exists():
        return pd.read_parquet(cache_path)

    df = fetch_nasa_power(location.lat, location.lon)
    if cache:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(cache_path, index=False)
    return df


def fetch_sleman_centroid(cache: bool = True) -> pd.DataFrame:
    """Deprecated alias."""
    from wef_agentic.geo.presets import SLEMAN

    return fetch_for_location(SLEMAN, cache=cache)
