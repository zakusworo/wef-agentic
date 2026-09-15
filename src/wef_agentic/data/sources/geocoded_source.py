"""Geocoded population source — population attached to a geocoding match (GeoNames)."""
from __future__ import annotations

from typing import ClassVar

from wef_agentic.data.sources.base import DataPacket, DataSource, DataSourceUnavailable
from wef_agentic.geo.location import Location


class GeocodedPopulationSource(DataSource):
    """Population from the Open-Meteo geocoding hit (GeoNames gazetteer).

    Sub-national, unlike World Bank country totals, but may describe the city
    proper rather than the administrative region, and its reference year is unknown.
    """

    name = "geocoding-gazetteer"
    tier = 2
    supported_variables: ClassVar[set[str]] = {"socio.population"}

    def supports(self, variable: str, location: Location) -> bool:
        return variable in self.supported_variables and bool(location.population)

    def fetch(self, variable: str, location: Location) -> DataPacket:
        if not self.supports(variable, location):
            raise DataSourceUnavailable(f"No gazetteer population for {location.display}")
        return DataPacket(
            variable=variable,
            value=int(location.population),
            location=location.to_dict(),
            source=self.name,
            unit="jiwa",
            confidence=0.7,
            tier=self.tier,
            note=(
                "Populasi dari GeoNames via Open-Meteo geocoding; tahun referensi tidak "
                "diketahui dan bisa merujuk kota inti, bukan wilayah administratif."
            ),
        )
