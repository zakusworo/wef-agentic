"""Geo package — Location + geocoding + presets."""
from wef_agentic.geo.geocoding import geocode, geocode_first
from wef_agentic.geo.location import Location
from wef_agentic.geo.presets import PRESETS, SLEMAN, get_preset, list_presets

__all__ = [
    "PRESETS",
    "SLEMAN",
    "Location",
    "clear_location_cache",
    "geocode",
    "geocode_first",
    "get_preset",
    "list_presets",
    "remember_location",
    "resolve_location",
]

# Per-process cache: one geocoding call per query, and the UI can pin the exact
# match the user picked (geocoding the bare name again may return a different city).
_RESOLVED: dict[str, Location] = {}


def _key(query: str) -> str:
    return query.strip().lower()


def remember_location(query: str, location: Location) -> None:
    """Pin `query` to a specific Location for subsequent resolve_location calls."""
    _RESOLVED[_key(query)] = location


def clear_location_cache() -> None:
    _RESOLVED.clear()


def resolve_location(query: str) -> Location | None:
    """Cari di presets dulu, lalu cache, fallback ke geocoding live."""
    preset = get_preset(query)
    if preset is not None:
        return preset
    key = _key(query)
    if key in _RESOLVED:
        return _RESOLVED[key]
    location = geocode_first(query)
    if location is not None:
        _RESOLVED[key] = location
    return location
