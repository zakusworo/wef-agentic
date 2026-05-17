"""Country-defaults proxy source — last-resort fallback (tier 3)."""
from __future__ import annotations

from typing import ClassVar

from wef_agentic.data.country_defaults import (
    ELECTRICITY_PER_CAPITA_KWH,
    GRID_EMISSION_FACTOR,
    RICE_PER_CAPITA_KG,
    get_default,
)
from wef_agentic.data.sources.base import DataPacket, DataSource, DataSourceUnavailable
from wef_agentic.geo.location import Location


class CountryProxySource(DataSource):
    """Country-level static defaults — last-resort jika source lain gagal."""

    name = "country-proxy-defaults"
    tier = 3
    supported_variables: ClassVar[set[str]] = {
        "energy.consumption_kwh_per_capita",
        "food.rice_consumption_kg_per_capita",
        "grid.emission_factor_kg_co2_per_kwh",
    }

    def fetch(self, variable: str, location: Location) -> DataPacket:
        if variable not in self.supported_variables:
            raise DataSourceUnavailable(variable)

        cc = (location.country_code or "DEFAULT").upper()
        if variable == "energy.consumption_kwh_per_capita":
            value = get_default(ELECTRICITY_PER_CAPITA_KWH, cc)
            unit = "kWh/year"
        elif variable == "food.rice_consumption_kg_per_capita":
            value = get_default(RICE_PER_CAPITA_KG, cc)
            unit = "kg/year"
        elif variable == "grid.emission_factor_kg_co2_per_kwh":
            value = get_default(GRID_EMISSION_FACTOR, cc)
            unit = "kg CO2/kWh"
        else:
            raise DataSourceUnavailable(variable)

        return DataPacket(
            variable=variable,
            value=value,
            location=location.to_dict(),
            source=self.name,
            year=2024,
            unit=unit,
            confidence=0.55,   # last-resort proxy
            tier=self.tier,
            note=f"Country default ({cc}) — illustrative, BUKAN data lokal. Override via manual JSON untuk akurasi.",
        )
