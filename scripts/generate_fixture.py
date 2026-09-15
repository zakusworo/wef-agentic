"""Generate the synthetic Sleman Open-Meteo fixture for offline development.

Output: data/processed/openmeteo_sleman_1991-01-01_2024-12-31.parquet
        data/processed/openmeteo_sleman_monthly.parquet
        data/processed/openmeteo_sleman_annual.parquet
"""
from __future__ import annotations

from wef_agentic.config.settings import PROCESSED_DIR
from wef_agentic.data.fixture import write_sleman_fixture
from wef_agentic.data.openmeteo import aggregate_monthly, annual_summary


def main():
    print("Generating synthetic Sleman Open-Meteo fixture (1991-2024, 3 stations)...")
    daily_path = write_sleman_fixture(PROCESSED_DIR)
    print(f"✓ Daily: {daily_path}")

    import pandas as pd

    monthly = aggregate_monthly(pd.read_parquet(daily_path))
    monthly_path = PROCESSED_DIR / "openmeteo_sleman_monthly.parquet"
    monthly.to_parquet(monthly_path, index=False)
    print(f"✓ Monthly: {monthly_path} ({len(monthly)} rows)")

    annual = annual_summary(monthly)
    annual_path = PROCESSED_DIR / "openmeteo_sleman_annual.parquet"
    annual.to_parquet(annual_path, index=False)
    print(f"✓ Annual: {annual_path} ({len(annual)} rows)")

    chk = annual[(annual["station"] == "Mlati") & (annual["year"] == 2023)]
    if not chk.empty:
        row = chk.iloc[0]
        print("\nQuick sanity check (Mlati station, 2023):")
        print(f"  Precip: {row['precip_mm']:.0f} mm/year  (expected ~2000-2600 for Sleman)")
        print(f"  Tmean:  {row['tmean_c']:.1f} °C        (expected ~26)")
        print(f"  ET0:    {row['et0_mm']:.0f} mm/year   (expected ~1300-1500)")


if __name__ == "__main__":
    main()
