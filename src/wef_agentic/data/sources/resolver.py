"""DataResolver — coba sources dalam priority order, return first success."""
from __future__ import annotations

from dataclasses import dataclass, field

from wef_agentic.data.sources.base import DataPacket, DataSource, DataSourceUnavailable
from wef_agentic.data.sources.bps_static_source import BPSStaticSource
from wef_agentic.data.sources.manual_source import ManualOverrideSource
from wef_agentic.data.sources.openmeteo_source import OpenMeteoSource
from wef_agentic.data.sources.proxy_source import CountryProxySource
from wef_agentic.data.sources.worldbank_source import WorldBankSource
from wef_agentic.geo.location import Location


@dataclass
class ResolutionTrace:
    """Audit trail: source mana yang ditarik untuk variable mana."""

    variable: str
    succeeded_source: str = ""
    attempts: list[tuple[str, str]] = field(default_factory=list)  # (source, result)


class DataResolver:
    """Coba semua DataSource yang relevan dalam priority order.

    Priority (tier asc, lalu order pendaftaran):
    1. ManualOverrideSource (tier 1, user-curated) — paling authoritative
    2. BPSStaticSource (tier 1, Sleman) — hardcoded BPS
    3. OpenMeteoSource (tier 1, global climate)
    4. WorldBankSource (tier 2, country)
    5. CountryProxySource (tier 3, last resort)
    """

    def __init__(self, sources: list[DataSource] | None = None):
        if sources is None:
            sources = [
                ManualOverrideSource(),
                BPSStaticSource(),
                OpenMeteoSource(),
                WorldBankSource(),
                CountryProxySource(),
            ]
        self.sources = sources

    def resolve(self, variable: str, location: Location) -> tuple[DataPacket, ResolutionTrace]:
        """Try each source dalam order, return packet pertama yang sukses + trace."""
        trace = ResolutionTrace(variable=variable)
        for source in self.sources:
            if not source.supports(variable, location):
                trace.attempts.append((source.name, "not supported"))
                continue
            try:
                packet = source.fetch(variable, location)
                trace.attempts.append((source.name, "ok"))
                trace.succeeded_source = source.name
                return packet, trace
            except DataSourceUnavailable as e:
                trace.attempts.append((source.name, f"unavailable: {e}"))
            except Exception as e:
                trace.attempts.append((source.name, f"error: {e}"))

        raise DataSourceUnavailable(
            f"No source available for {variable} at {location.display}. "
            f"Attempts: {trace.attempts}"
        )

    def resolve_many(
        self, variables: list[str], location: Location,
    ) -> dict[str, tuple[DataPacket | None, ResolutionTrace]]:
        """Bulk resolve, returns dict variable → (packet | None, trace)."""
        result: dict[str, tuple[DataPacket | None, ResolutionTrace]] = {}
        for var in variables:
            try:
                packet, trace = self.resolve(var, location)
                result[var] = (packet, trace)
            except DataSourceUnavailable as e:
                trace = ResolutionTrace(variable=var)
                trace.attempts.append(("resolver", f"failed: {e}"))
                result[var] = (None, trace)
        return result
