"""World Bank Open Data API — country-level indicators, free, no key."""
from __future__ import annotations

from typing import ClassVar

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from wef_agentic.data.sources.base import DataPacket, DataSource, DataSourceUnavailable
from wef_agentic.geo.location import Location

WB_URL = "https://api.worldbank.org/v2/country/{country}/indicator/{indicator}"

# Variable → World Bank indicator code
# socio.population (SP.POP.TOTL) deliberately omitted: it is a country total and
# would silently replace a city/regency population.
INDICATOR_MAP = {
    "socio.gdp_per_capita_usd": "NY.GDP.PCAP.CD",
    "energy.consumption_kwh_per_capita": "EG.USE.ELEC.KH.PC",
}


class WorldBankSource(DataSource):
    """Country-level indicators dari World Bank API."""

    name = "world-bank-open-data"
    tier = 2   # secondary (country level, not local)
    supported_variables: ClassVar[set[str]] = set(INDICATOR_MAP.keys())

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=4))
    def _fetch_indicator(self, country_code: str, indicator: str) -> tuple[float, int, dict]:
        url = WB_URL.format(country=country_code.lower(), indicator=indicator)
        with httpx.Client(timeout=20) as client:
            r = client.get(url, params={"format": "json", "per_page": 10, "date": "2015:2024"})
            r.raise_for_status()
            data = r.json()
        if not isinstance(data, list) or len(data) < 2 or not data[1]:
            raise DataSourceUnavailable(f"World Bank: empty response for {indicator}")
        # Take latest non-null value
        for row in data[1]:
            if row.get("value") is not None:
                return float(row["value"]), int(row["date"]), row
        raise DataSourceUnavailable(f"World Bank: all-null for {indicator}")

    def fetch(self, variable: str, location: Location) -> DataPacket:
        if variable not in INDICATOR_MAP:
            raise DataSourceUnavailable(f"Unsupported variable: {variable}")
        if not location.country_code:
            raise DataSourceUnavailable("World Bank requires country_code")

        indicator = INDICATOR_MAP[variable]
        try:
            value, year, raw = self._fetch_indicator(location.country_code, indicator)
        except DataSourceUnavailable:
            raise
        except Exception as e:
            raise DataSourceUnavailable(f"World Bank fetch failed: {e}") from e

        unit = {
            "socio.gdp_per_capita_usd": "USD",
            "energy.consumption_kwh_per_capita": "kWh/year",
        }[variable]

        return DataPacket(
            variable=variable,
            value=value,
            location=location.to_dict(),
            source=self.name,
            year=year,
            unit=unit,
            confidence=0.75,    # country average ≠ local
            tier=self.tier,
            note=f"Country-level mean ({location.country_code}) dari World Bank, indicator {indicator} tahun {year}. Untuk konteks sub-national bersifat proxy.",
            raw={"indicator": indicator, "wb_row": raw},
        )
