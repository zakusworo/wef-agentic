"""Geo package — Location + geocoding + presets."""
from wef_agentic.geo.geocoding import geocode, geocode_first
from wef_agentic.geo.location import Location
from wef_agentic.geo.presets import PRESETS, SLEMAN, get_preset, list_presets

__all__ = [
    "PRESETS",
    "SLEMAN",
    "Location",
    "geocode",
    "geocode_first",
    "get_preset",
    "list_presets",
]


def resolve_location(query: str) -> Location | None:
    """Cari di presets dulu, fallback ke geocoding live."""
    preset = get_preset(query)
    if preset is not None:
        return preset
    return geocode_first(query)
