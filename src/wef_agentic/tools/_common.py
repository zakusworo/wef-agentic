"""Shared helpers for tool implementations: location + provenance-aware data resolution."""
from __future__ import annotations

import pandas as pd

from wef_agentic.config.settings import load_nexus_config
from wef_agentic.data.sources import DataPacket, DataResolver, DataSourceUnavailable
from wef_agentic.geo import Location, resolve_location

_RESOLVER: DataResolver | None = None


def resolver() -> DataResolver:
    global _RESOLVER
    if _RESOLVER is None:
        _RESOLVER = DataResolver()
    return _RESOLVER


def resolve_or_raise(location_query: str) -> Location:
    loc = resolve_location(location_query)
    if loc is None:
        raise ValueError(f"Tidak dapat resolve location: '{location_query}'")
    return loc


def resolve_packet(variable: str, location: Location) -> DataPacket | None:
    """Highest-priority available DataPacket for `variable`, or None."""
    try:
        packet, _trace = resolver().resolve(variable, location)
    except DataSourceUnavailable:
        return None
    return packet


def resolve_population(location: Location) -> tuple[int, dict]:
    """Population + provenance. Falls back to a flagged low-confidence constant."""
    packet = resolve_packet("socio.population", location)
    if packet is not None:
        return int(packet.value), packet.to_dict()

    fallback = int(
        (load_nexus_config().get("fallbacks") or {}).get("population_when_unknown", 100_000)
    )
    return fallback, {
        "variable": "socio.population",
        "value": fallback,
        "location": location.to_dict(),
        "source": "fallback-constant",
        "fetched_at": None,
        "year": None,
        "unit": "jiwa",
        "confidence": 0.1,
        "tier": 3,
        "note": (
            "Populasi tidak diketahui — konstanta fallback dari config/nexus.yaml. "
            "Angka per kapita (demand, SSL) tidak dapat dipakai untuk keputusan."
        ),
    }


def value_at(yearly: pd.DataFrame, year: int, column: str) -> float | None:
    row = yearly.loc[yearly["year"] == year, column]
    return float(row.iloc[0]) if not row.empty else None


def sample_yearly(yearly: pd.DataFrame, columns: list[str] | None = None, n: int = 6) -> list[dict]:
    """~n evenly spaced rows for prompts/charts, always including the final year."""
    df = yearly if columns is None else yearly[columns]
    idx = list(range(0, len(df), max(1, len(df) // n)))
    if idx[-1] != len(df) - 1:
        idx.append(len(df) - 1)
    return df.iloc[idx].round(1).to_dict(orient="records")
