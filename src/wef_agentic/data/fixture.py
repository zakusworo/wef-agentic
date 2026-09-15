"""Synthetic Open-Meteo fixture untuk Sleman — offline development & tests.

Synthetic data mengikuti pola iklim tropis monsun Sleman:
- Curah hujan tinggi Nov-Apr (musim hujan), rendah Mei-Okt (kemarau)
- Suhu rata-rata 26°C, low variability annual
- ET0 berkebalikan dengan precip (tinggi di musim kemarau)
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from wef_agentic.data.constants import DEFAULT_END, DEFAULT_START, SLEMAN_STATIONS

# Monthly normal precip pattern (mm/day average), kalibrasi BPS-BMKG Sleman ~2200 mm/year
MONTHLY_PRECIP_MEAN = {
    1: 16.0, 2: 15.0, 3: 13.0, 4: 9.5, 5: 6.0, 6: 3.0,
    7: 2.0, 8: 1.5, 9: 3.5, 10: 7.5, 11: 12.5, 12: 15.0,
}
MONTHLY_TMEAN = {
    1: 26.2, 2: 26.0, 3: 26.4, 4: 26.6, 5: 26.7, 6: 26.3,
    7: 25.8, 8: 26.0, 9: 26.7, 10: 27.2, 11: 27.0, 12: 26.5,
}
# Pakem (utara, gunung) lebih dingin & lebih basah; Prambanan sedikit lebih kering
STATION_ADJUST = {"Pakem": (1.15, -1.5), "Prambanan": (0.90, 0.3)}


def synth_daily(
    lat: float, lon: float, station: str, zone: str, rng: np.random.Generator,
    start: str = DEFAULT_START, end: str = DEFAULT_END,
) -> pd.DataFrame:
    """Generate daily synthetic data untuk satu stasiun."""
    dates = pd.date_range(start, end, freq="D")
    n = len(dates)
    precip_mult, temp_offset = STATION_ADJUST.get(station, (1.0, 0.0))
    months_idx = dates.month.values

    precip = np.array([rng.gamma(2.0, MONTHLY_PRECIP_MEAN[m] * precip_mult / 2.0) for m in months_idx])
    precip = np.where(rng.random(n) < 0.20, 0.0, precip)  # 20% dry days (tropical)

    tmean = np.array([MONTHLY_TMEAN[m] + temp_offset + rng.normal(0, 1.2) for m in months_idx])
    tmax = tmean + rng.uniform(3.5, 6.0, n)
    tmin = tmean - rng.uniform(3.0, 5.5, n)

    rh = np.clip(75 + 15 * (precip > 5) + rng.normal(0, 5, n), 50, 100)
    wind = np.clip(rng.gamma(2, 1.5, n), 0.5, 12)

    # ET0 (Hargreaves-Samani proxy, Ra ≈ 30-38 MJ/m²/day near equator)
    srad_ra = np.clip(33 + 4 * np.cos(2 * np.pi * (months_idx - 4) / 12) + rng.normal(0, 1.5, n), 22, 40)
    et0 = np.clip(0.0023 * (tmax - tmin) ** 0.5 * (tmean + 17.8) * srad_ra * 0.408, 2.5, 7.5)
    srad = np.clip(15 + 7 * np.cos(2 * np.pi * (months_idx - 4) / 12) + rng.normal(0, 2, n), 5, 28)

    return pd.DataFrame(
        {
            "date": dates,
            "lat": lat,
            "lon": lon,
            "temperature_2m_max": tmax,
            "temperature_2m_min": tmin,
            "temperature_2m_mean": tmean,
            "precipitation_sum": precip,
            "relative_humidity_2m_mean": rh,
            "wind_speed_10m_max": wind,
            "shortwave_radiation_sum": srad,
            "et0_fao_evapotranspiration": et0,
            "station": station,
            "zone": zone,
        }
    )


def build_sleman_daily(seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    frames = [synth_daily(st["lat"], st["lon"], st["name"], st["zone"], rng) for st in SLEMAN_STATIONS]
    return pd.concat(frames, ignore_index=True)


def sleman_fixture_path(processed_dir: Path) -> Path:
    """Path that data.openmeteo._fetch_sleman_stations reads as its cache."""
    return processed_dir / f"openmeteo_sleman_{DEFAULT_START}_{DEFAULT_END}.parquet"


def write_sleman_fixture(processed_dir: Path, seed: int = 42) -> Path:
    processed_dir.mkdir(parents=True, exist_ok=True)
    path = sleman_fixture_path(processed_dir)
    build_sleman_daily(seed).to_parquet(path, index=False)
    return path
