"""Data sources framework — pluggable real-time data fetching dengan provenance."""
from wef_agentic.data.sources.base import (
    DataPacket,
    DataSource,
    DataSourceUnavailable,
)
from wef_agentic.data.sources.bps_static_source import BPSStaticSource
from wef_agentic.data.sources.geocoded_source import GeocodedPopulationSource
from wef_agentic.data.sources.manual_source import ManualOverrideSource
from wef_agentic.data.sources.openmeteo_source import OpenMeteoSource
from wef_agentic.data.sources.proxy_source import CountryProxySource
from wef_agentic.data.sources.registry import (
    VARIABLES,
    VariableSpec,
    get_variable,
    list_variables,
    manual_override_schema,
)
from wef_agentic.data.sources.resolver import DataResolver, ResolutionTrace
from wef_agentic.data.sources.worldbank_source import WorldBankSource

__all__ = [
    "VARIABLES",
    "BPSStaticSource",
    "CountryProxySource",
    "DataPacket",
    "DataResolver",
    "DataSource",
    "DataSourceUnavailable",
    "GeocodedPopulationSource",
    "ManualOverrideSource",
    "OpenMeteoSource",
    "ResolutionTrace",
    "VariableSpec",
    "WorldBankSource",
    "get_variable",
    "list_variables",
    "manual_override_schema",
]


def fetch_all_for_location(location, variables: list[str] | None = None) -> dict:
    """Convenience helper — resolve all (or specified) variables untuk location."""
    if variables is None:
        variables = list(VARIABLES.keys())
    resolver = DataResolver()
    return resolver.resolve_many(variables, location)
