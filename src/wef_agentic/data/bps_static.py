"""BPS Sleman — static data hardcoded dari publikasi resmi.

Mengikuti rekomendasi WEF-Agentic.md §12 (risk mitigation untuk BPS data format inkonsisten):
hardcode angka kunci dari Statistik Daerah Kabupaten Sleman + Statistik Pertanian.

Sumber:
- BPS Kabupaten Sleman, Statistik Daerah Kabupaten Sleman (2024, 2023, 2022)
- BPS, Sleman Dalam Angka (2024)
- Distan Sleman, Laporan Tahunan
Angka adalah approximasi publik untuk MVP demo. Akan di-replace dengan scraping
otomatis di Phase 1.
"""
from __future__ import annotations

import pandas as pd

# Populasi Sleman per tahun (jiwa)
POPULATION = {
    2015: 1167481,
    2018: 1180479,
    2020: 1125804,  # SP2020
    2021: 1130090,
    2022: 1134869,
    2023: 1138691,
    2024: 1142528,  # proyeksi
}

# PDRB per kapita (juta IDR, harga konstan 2010)
PDRB_PER_CAPITA = {
    2018: 32.5,
    2019: 33.8,
    2020: 32.1,  # COVID
    2021: 33.4,
    2022: 35.2,
    2023: 37.1,
}

# Luas panen padi (ha) — Sleman
RICE_HARVEST_AREA = {
    2018: 44000,
    2019: 42500,
    2020: 41200,
    2021: 40500,
    2022: 39800,
    2023: 39000,  # tren penurunan akibat alih fungsi LP2B
}

# Produktivitas padi (ton/ha)
RICE_YIELD = {
    2018: 6.4,
    2019: 6.5,
    2020: 6.3,
    2021: 6.5,
    2022: 6.6,
    2023: 6.5,
}

# Konsumsi listrik Sleman (GWh) — approximasi dari ESDM Statistik Ketenagalistrikan
ELECTRICITY_CONSUMPTION = {
    2018: 1450,
    2019: 1530,
    2020: 1520,  # flat COVID
    2021: 1610,
    2022: 1740,
    2023: 1880,
}

# Alih fungsi sawah ke non-sawah (ha/tahun) — estimasi dari Distan & studi UGM
RICE_LAND_LOSS_PER_YEAR = 280  # rata-rata 2015-2023


def get_dataframe(series_name: str) -> pd.DataFrame:
    """Convert dict → DataFrame untuk dipakai model & agen."""
    series_map = {
        "population": POPULATION,
        "pdrb_per_capita": PDRB_PER_CAPITA,
        "rice_harvest_area_ha": RICE_HARVEST_AREA,
        "rice_yield_t_ha": RICE_YIELD,
        "electricity_gwh": ELECTRICITY_CONSUMPTION,
    }
    if series_name not in series_map:
        raise KeyError(f"Unknown series: {series_name}. Available: {list(series_map)}")

    data = series_map[series_name]
    return pd.DataFrame(
        {"year": list(data.keys()), series_name: list(data.values())}
    )


def all_series() -> pd.DataFrame:
    """Return merged DataFrame dengan semua series, indexed by year."""
    frames = []
    for name in ["population", "pdrb_per_capita", "rice_harvest_area_ha",
                 "rice_yield_t_ha", "electricity_gwh"]:
        frames.append(get_dataframe(name).set_index("year"))
    return pd.concat(frames, axis=1).reset_index()
