"""Open-Meteo data source — global, free, no API key."""
from __future__ import annotations

from typing import ClassVar

from wef_agentic.data.openmeteo import (
    aggregate_monthly,
    annual_summary,
    fetch_climate_for_location,
)
from wef_agentic.data.sources.base import DataPacket, DataSource, DataSourceUnavailable
from wef_agentic.geo.location import Location


class OpenMeteoSource(DataSource):
    """Climate variables via Open-Meteo Historical API."""

    name = "open-meteo-historical"
    tier = 1   # primary (authoritative ERA5-based reanalysis)
    supported_variables: ClassVar[set[str]] = {
        "climate.precip_mm_annual",
        "climate.temp_c_mean",
        "climate.et0_mm_annual",
    }

    def fetch(self, variable: str, location: Location) -> DataPacket:
        if variable not in self.supported_variables:
            raise DataSourceUnavailable(f"Unsupported variable: {variable}")

        try:
            df = fetch_climate_for_location(location)
        except Exception as e:
            raise DataSourceUnavailable(f"Open-Meteo fetch failed: {e}") from e

        monthly = aggregate_monthly(df)
        annual = annual_summary(monthly)
        # Filter recent years for representative mean (last 10 years)
        years = sorted(annual["year"].unique())
        recent_years = years[-10:] if len(years) >= 10 else years
        recent = annual[annual["year"].isin(recent_years)]

        if variable == "climate.precip_mm_annual":
            value = float(recent["precip_mm"].mean())
            unit = "mm/year"
        elif variable == "climate.temp_c_mean":
            value = float(recent["tmean_c"].mean())
            unit = "°C"
        elif variable == "climate.et0_mm_annual":
            value = float(recent["et0_mm"].mean())
            unit = "mm/year"
        else:
            raise DataSourceUnavailable(variable)

        return DataPacket(
            variable=variable,
            value=round(value, 2),
            location=location.to_dict(),
            source=self.name,
            year=int(recent_years[-1]),
            unit=unit,
            confidence=0.92,
            tier=self.tier,
            note=f"10-year mean ({recent_years[0]}-{recent_years[-1]}) dari Open-Meteo Historical (ERA5)",
        )
