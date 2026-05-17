"""BPS Static Source — hardcoded data BPS Sleman.

Untuk lokasi non-Sleman, source ini tidak supported (skip).
Future: BPS WebAPI (butuh registration key).
"""
from __future__ import annotations

from typing import ClassVar

from wef_agentic.data.bps_static import (
    ELECTRICITY_CONSUMPTION,
    POPULATION,
    RICE_HARVEST_AREA,
    RICE_YIELD,
)
from wef_agentic.data.sources.base import DataPacket, DataSource, DataSourceUnavailable
from wef_agentic.geo.location import Location


class BPSStaticSource(DataSource):
    """Hardcoded BPS Sleman — paling authoritative untuk Sleman."""

    name = "bps-sleman-static"
    tier = 1
    supported_variables: ClassVar[set[str]] = {
        "socio.population",
        "energy.consumption_gwh_annual",
        "food.rice_area_ha",
        "food.rice_yield_t_per_ha",
    }

    def supports(self, variable: str, location: Location) -> bool:
        # Only Sleman preset
        if not (location.name == "Sleman" and location.source == "preset"):
            return False
        return super().supports(variable, location)

    def fetch(self, variable: str, location: Location) -> DataPacket:
        if not self.supports(variable, location):
            raise DataSourceUnavailable(f"BPS static: not applicable for {location.display}")

        latest_year = 2023
        if variable == "socio.population":
            value = POPULATION[latest_year]
            unit = "jiwa"
            note = "BPS Sleman, Data Agregat per Kabupaten 2023."
        elif variable == "energy.consumption_gwh_annual":
            value = ELECTRICITY_CONSUMPTION[latest_year]
            unit = "GWh/year"
            note = "ESDM + estimasi proporsional PLN ULP Mungkid."
        elif variable == "food.rice_area_ha":
            value = RICE_HARVEST_AREA[latest_year]
            unit = "ha"
            note = "BPS Sleman, Statistik Pertanian 2023."
        elif variable == "food.rice_yield_t_per_ha":
            value = RICE_YIELD[latest_year]
            unit = "t/ha"
            note = "BPS Sleman, Statistik Pertanian 2023."
        else:
            raise DataSourceUnavailable(variable)

        return DataPacket(
            variable=variable,
            value=value,
            location=location.to_dict(),
            source=self.name,
            year=latest_year,
            unit=unit,
            confidence=0.95,
            tier=self.tier,
            note=note,
        )
