"""Generate synthetic Open-Meteo fixture untuk smoke test / offline development.

Output: data/processed/openmeteo_sleman_1991-01-01_2024-12-31.parquet
        data/processed/openmeteo_sleman_monthly.parquet
        data/processed/openmeteo_sleman_annual.parquet

Synthetic data mengikuti pola iklim tropis monsun Sleman:
- Curah hujan tinggi Nov-Apr (musim hujan), rendah Mei-Okt (kemarau)
- Suhu rata-rata 26°C, low variability annual
- ET0 berkebalikan dengan precip (tinggi di musim kemarau)
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wef_agentic.config.settings import PROCESSED_DIR
from wef_agentic.data.constants import SLEMAN_STATIONS

rng = np.random.default_rng(42)


def synth_daily(lat: float, lon: float, station: str, zone: str) -> pd.DataFrame:
    """Generate daily synthetic data Sleman 1991-2024."""
    dates = pd.date_range("1991-01-01", "2024-12-31", freq="D")
    n = len(dates)

    # Monthly normal precip pattern (mm/day average, Sleman tropical monsoon)
    # Kalibrasi terhadap BPS-BMKG Sleman ~2200 mm/year
    monthly_precip_mean = {
        1: 16.0, 2: 15.0, 3: 13.0, 4: 9.5, 5: 6.0, 6: 3.0,
        7: 2.0, 8: 1.5, 9: 3.5, 10: 7.5, 11: 12.5, 12: 15.0,
    }
    # Suhu rata-rata bulanan
    monthly_tmean = {
        1: 26.2, 2: 26.0, 3: 26.4, 4: 26.6, 5: 26.7, 6: 26.3,
        7: 25.8, 8: 26.0, 9: 26.7, 10: 27.2, 11: 27.0, 12: 26.5,
    }
    # Stations sedikit beda; Pakem (utara, gunung) lebih dingin & lebih basah
    if station == "Pakem":
        precip_mult = 1.15
        temp_offset = -1.5
    elif station == "Prambanan":
        precip_mult = 0.90
        temp_offset = 0.3
    else:
        precip_mult = 1.0
        temp_offset = 0.0

    months_idx = dates.month.values

    precip = np.array([rng.gamma(2.0, monthly_precip_mean[m] * precip_mult / 2.0) for m in months_idx])
    precip = np.where(rng.random(n) < 0.20, 0.0, precip)  # 20% dry days (tropical)

    tmean = np.array([monthly_tmean[m] + temp_offset + rng.normal(0, 1.2) for m in months_idx])
    tmax = tmean + rng.uniform(3.5, 6.0, n)
    tmin = tmean - rng.uniform(3.0, 5.5, n)

    rh = np.clip(75 + 15 * (precip > 5) + rng.normal(0, 5, n), 50, 100)
    wind = np.clip(rng.gamma(2, 1.5, n), 0.5, 12)

    # ET0 (Hargreaves-Samani proxy menggunakan Ra-equivalent, kalibrasi ~4 mm/day tropical)
    # Ra (extraterrestrial radiation) ≈ 30-38 MJ/m²/day near equator
    srad_ra = np.clip(33 + 4 * np.cos(2 * np.pi * (months_idx - 4) / 12) + rng.normal(0, 1.5, n), 22, 40)
    et0 = np.clip(0.0023 * (tmax - tmin) ** 0.5 * (tmean + 17.8) * srad_ra * 0.408, 2.5, 7.5)
    # Simpan srad observasi (surface shortwave) terpisah untuk realism
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


def main():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    print("Generating synthetic Sleman Open-Meteo fixture (1991-2024, 3 stations)...")
    frames = []
    for st in SLEMAN_STATIONS:
        df = synth_daily(st["lat"], st["lon"], st["name"], st["zone"])
        frames.append(df)
    daily = pd.concat(frames, ignore_index=True)

    daily_path = PROCESSED_DIR / "openmeteo_sleman_1991-01-01_2024-12-31.parquet"
    daily.to_parquet(daily_path, index=False)
    print(f"✓ Daily: {daily_path} ({len(daily)} rows)")

    # Monthly aggregation
    from wef_agentic.data.openmeteo import aggregate_monthly, annual_summary
    monthly = aggregate_monthly(daily)
    monthly_path = PROCESSED_DIR / "openmeteo_sleman_monthly.parquet"
    monthly.to_parquet(monthly_path, index=False)
    print(f"✓ Monthly: {monthly_path} ({len(monthly)} rows)")

    annual = annual_summary(monthly)
    annual_path = PROCESSED_DIR / "openmeteo_sleman_annual.parquet"
    annual.to_parquet(annual_path, index=False)
    print(f"✓ Annual: {annual_path} ({len(annual)} rows)")

    # Verifikasi cepat
    print("\nQuick sanity check (Mlati station, 2023):")
    chk = annual[(annual["station"] == "Mlati") & (annual["year"] == 2023)]
    if not chk.empty:
        row = chk.iloc[0]
        print(f"  Precip: {row['precip_mm']:.0f} mm/year  (expected ~2000-2300 for Sleman)")
        print(f"  Tmean:  {row['tmean_c']:.1f} °C        (expected ~26)")
        print(f"  ET0:    {row['et0_mm']:.0f} mm/year   (expected ~1300-1500)")


if __name__ == "__main__":
    main()
