"""Open-Meteo Geocoding API — free, no key required.

Docs: https://open-meteo.com/en/docs/geocoding-api
"""
from __future__ import annotations

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from wef_agentic.geo.location import Location

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5))
def geocode(name: str, count: int = 5, language: str = "en") -> list[Location]:
    """Cari lokasi berdasarkan nama. Return list (multiple matches mungkin)."""
    if not name or len(name.strip()) < 2:
        return []

    params = {"name": name.strip(), "count": count, "language": language, "format": "json"}
    with httpx.Client(timeout=15) as client:
        r = client.get(GEOCODING_URL, params=params)
        r.raise_for_status()
        data = r.json()

    results = data.get("results") or []
    locations: list[Location] = []
    for hit in results:
        loc = Location(
            name=hit.get("name", name),
            lat=hit.get("latitude", 0.0),
            lon=hit.get("longitude", 0.0),
            country=hit.get("country", ""),
            country_code=hit.get("country_code", ""),
            admin1=hit.get("admin1", ""),
            admin2=hit.get("admin2", ""),
            population=hit.get("population"),
            timezone=hit.get("timezone", "UTC"),
            elevation_m=hit.get("elevation"),
            source="geocoded",
            metadata={"raw": hit},
        )
        locations.append(loc)
    return locations


def geocode_first(name: str) -> Location | None:
    """Convenience: ambil match pertama saja."""
    results = geocode(name, count=1)
    return results[0] if results else None
