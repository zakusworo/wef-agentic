"""Bootstrap data fetching — jalankan sekali setelah install untuk cache dataset."""
from __future__ import annotations

import argparse
import sys

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from wef_agentic.data.nasa_power import fetch_sleman_centroid
from wef_agentic.data.openmeteo import (
    aggregate_monthly,
    annual_summary,
    fetch_sleman_stations,
)

console = Console()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="replace existing climate caches with live data")
    args = parser.parse_args()
    console.rule("[bold cyan]WEF-Agentic Data Bootstrap")

    tasks = [
        ("Open-Meteo: 3 stasiun Sleman, 1991–2024", lambda: _bootstrap_openmeteo(args.force)),
        ("NASA POWER: centroid Sleman, 1991–2024", _bootstrap_nasa_power),
    ]

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        for label, fn in tasks:
            task_id = progress.add_task(label, total=None)
            try:
                fn()
                progress.update(task_id, description=f"[green]✓[/green] {label}")
            except Exception as e:
                progress.update(task_id, description=f"[red]✗[/red] {label}: {e}")
                console.print_exception()
                return 1

    console.rule("[bold green]Bootstrap selesai")
    console.print(
        "[dim]Cache disimpan di data/processed/. "
        "Re-run aman (akan skip jika sudah ada).[/dim]"
    )
    return 0


def _bootstrap_openmeteo(force: bool = False) -> None:
    df = fetch_sleman_stations(cache=not force)
    monthly = aggregate_monthly(df)
    annual = annual_summary(monthly)
    # Save aggregated views juga
    from wef_agentic.config.settings import PROCESSED_DIR
    from wef_agentic.data.openmeteo import DEFAULT_END, DEFAULT_START
    if force:
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        df.to_parquet(PROCESSED_DIR / f"openmeteo_sleman_{DEFAULT_START}_{DEFAULT_END}.parquet", index=False)
    monthly.to_parquet(PROCESSED_DIR / "openmeteo_sleman_monthly.parquet", index=False)
    annual.to_parquet(PROCESSED_DIR / "openmeteo_sleman_annual.parquet", index=False)


def _bootstrap_nasa_power() -> None:
    fetch_sleman_centroid()


if __name__ == "__main__":
    sys.exit(main())
