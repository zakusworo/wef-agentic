"""Country-level defaults untuk lokasi non-Indonesia.

Sumber:
- Per-capita electricity: IEA / World Bank (rata-rata terkini 2022-2024)
- Per-capita rice consumption: FAOSTAT
- GDP per capita growth: World Bank trends 2010-2023
Default disengaja konservatif; reviewer harus tahu ini illustrative.
"""
from __future__ import annotations

# Per-capita electricity consumption (kWh/capita/year)
ELECTRICITY_PER_CAPITA_KWH = {
    "ID": 1100,    # Indonesia
    "MY": 5000,    # Malaysia
    "TH": 2900,    # Thailand
    "VN": 2700,    # Vietnam
    "PH": 850,     # Philippines
    "IN": 1300,    # India
    "CN": 5500,    # China
    "JP": 7800,    # Japan
    "KR": 11000,   # South Korea
    "US": 12000,   # USA
    "DE": 6500,    # Germany
    "FR": 6500,    # France
    "UK": 4400,    # UK
    "BR": 2700,    # Brazil
    "MX": 2200,    # Mexico
    "ZA": 3500,    # South Africa
    "EG": 1700,    # Egypt
    "MA": 1000,    # Morocco
    "NG": 150,     # Nigeria
    "KE": 170,     # Kenya
    "AU": 10000,   # Australia
    "DEFAULT": 2500,
}

# Per-capita rice consumption (kg/capita/year)
RICE_PER_CAPITA_KG = {
    "ID": 115,
    "MY": 80,
    "TH": 100,
    "VN": 145,
    "PH": 110,
    "IN": 70,
    "CN": 76,
    "JP": 50,
    "KR": 55,
    "BD": 175,
    "MA": 5,       # gandum-dominant
    "EG": 38,
    "US": 7,
    "DEFAULT": 60,
}

# GDP per capita growth (annual %, recent trend)
GDP_PER_CAPITA_GROWTH = {
    "ID": 4.5,
    "MY": 3.5,
    "TH": 2.5,
    "VN": 5.5,
    "PH": 4.0,
    "IN": 5.5,
    "CN": 5.0,
    "JP": 0.8,
    "KR": 2.0,
    "US": 1.5,
    "DE": 1.0,
    "MA": 3.0,
    "DEFAULT": 2.0,
}

# Population growth (%/year)
POPULATION_GROWTH = {
    "ID": 0.7,
    "MY": 1.0,
    "TH": 0.1,
    "VN": 0.8,
    "PH": 1.4,
    "IN": 0.8,
    "CN": -0.1,
    "JP": -0.5,
    "KR": -0.2,
    "US": 0.4,
    "DE": 0.1,
    "MA": 1.1,
    "DEFAULT": 0.8,
}

# Grid emission factor (kg CO2/kWh)
GRID_EMISSION_FACTOR = {
    "ID": 0.85,   # Jawa-Bali grid coal-heavy
    "MY": 0.65,
    "TH": 0.45,
    "VN": 0.55,
    "PH": 0.65,
    "IN": 0.80,
    "CN": 0.55,
    "JP": 0.45,
    "KR": 0.45,
    "US": 0.40,
    "DE": 0.35,
    "FR": 0.06,   # nuclear-heavy
    "MA": 0.65,
    "DEFAULT": 0.55,
}


def get_default(table: dict, country_code: str, fallback_key: str = "DEFAULT"):
    cc = (country_code or "").upper()
    return table.get(cc, table.get(fallback_key))
