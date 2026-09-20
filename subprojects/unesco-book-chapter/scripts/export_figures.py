"""Export chapter demonstration figures from saved synthetic runs, without LLM calls."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from wef_agentic.reporting import generate_scenario_report
from wef_agentic.ui.demo import load_demo

SUBPROJECT = Path(__file__).resolve().parents[1]
ROOT = SUBPROJECT.parents[1]
FIGURES = SUBPROJECT / "figures"
EVIDENCE = SUBPROJECT / "evidence"
LABEL = "Synthetic climate; uncalibrated screening parameters"


def save(fig, name, label=LABEL):
    fig.text(0.5, 0.015, label, ha="center", fontsize=8)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    for suffix in ("png", "svg", "pdf"):
        fig.savefig(FIGURES / f"{name}.{suffix}", dpi=300, bbox_inches="tight")
    plt.close(fig)


def main():
    FIGURES.mkdir(parents=True, exist_ok=True)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    source = ROOT / "docs/runs/sweep_synthetic_20260920.json"
    sweep = json.loads(source.read_text())
    demo = load_demo()
    monthly = demo.nexus.water_balance["monthly"]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    months = [r["month"] for r in monthly]
    for key, label, color in (("precip_mm", "Precipitation", "#2367a1"),
                               ("et0_mm", "Reference evapotranspiration", "#a85419"),
                               ("deficit_mm", "Water deficit", "#ac2637")):
        ax.plot(months, [r[key] for r in monthly], marker="o", label=label, color=color)
    ax.set(xlabel="Month", ylabel="Water depth (mm/month)", xticks=months,
           title="S2: Seasonal water balance, Mlati, 2023 climate baseline")
    ax.legend(frameon=False, fontsize=9)
    ax.grid(axis="y", alpha=0.2)
    save(fig, "fig01-synthetic-seasonal-water")

    rows = []
    for row in sweep["results"]:
        n = row["nexus"]
        rows.append({"scenario": row["id"],
                     "stress": n["coupling"]["water_stress_effective"],
                     "pumping_delta_gwh": n["coupling"]["extra_pumping_demand_gwh"],
                     "yield_t_ha": n["crop_projection"]["endpoints"]["yield_t_ha"],
                     "ssl_2030": n["food_ssl"]["ssl"]})
    with (EVIDENCE / "synthetic-scenario-metrics.csv").open("w") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    fig, axes = plt.subplots(1, 3, figsize=(11, 4))
    labels = [r["scenario"].split("_")[0] for r in rows]
    for ax, key, title in zip(axes, ("stress", "pumping_delta_gwh", "ssl_2030"),
                              ("Water stress (fraction)", "Pumping change (GWh/year)",
                               "Rice self-sufficiency, 2030"), strict=True):
        ax.bar(labels, [r[key] for r in rows], color="#2367a1")
        ax.axhline(0, color="black", linewidth=0.6)
        ax.set_title(title, fontsize=10)
        ax.grid(axis="y", alpha=0.2)
    save(fig, "fig02-synthetic-scenario-comparison")

    record_path = ROOT / "docs/runs/run_S2_JETP_Aligned_sleman_claude-agent-sdk_20260920_143021.json"
    record = json.loads(record_path.read_text())
    fig, ax = plt.subplots(figsize=(7, 4))
    names = [a["name"].title() for a in record["agents"]]
    ax.bar(names, [record["timings_sec"][a["name"]] for a in record["agents"]], color="#427b50")
    ax.set(ylabel="Elapsed time per agent (seconds)",
           title="Recorded Claude demonstration: one run")
    ax.text(0.02, 0.96, "Domain agents run concurrently; bar heights are not additive",
            transform=ax.transAxes, va="top", fontsize=8)
    save(fig, "fig03-live-agent-timings")

    real_paths = [ROOT / "docs/runs/sweep_openmeteo_20260920.json",
                  ROOT / "docs/runs/sweep_openmeteo_2015_20260920.json"]
    if all(p.exists() for p in real_paths):
        fig, ax = plt.subplots(figsize=(8, 4.5))
        for p, year in zip(real_paths, (2023, 2015), strict=True):
            results = json.loads(p.read_text())["results"]
            ax.plot([r["id"].split("_")[0] for r in results],
                    [r["nexus"]["coupling"]["water_stress_effective"] for r in results],
                    marker="o", label=f"{year} historical climate baseline")
        ax.set(ylabel="Water stress after assumed irrigation (fraction)",
               title="Scenario stress with downloaded Open-Meteo climate")
        ax.legend(frameon=False)
        ax.grid(axis="y", alpha=0.2)
        save(fig, "fig04-openmeteo-baseline-comparison",
             "Downloaded historical climate; irrigation and crop parameters remain uncalibrated")

    demo.nexus.warnings.insert(0, "DEMO ONLY: synthetic climate, uncalibrated parameters; not observed outcomes.")
    (EVIDENCE / "demo-synthetic-report.pdf").write_bytes(generate_scenario_report(demo))
    manifest = {"data_class": "fig01–03 synthetic demo; fig04 downloaded climate, uncalibrated",
                "inputs": {}, "figures": {}}
    for p in (source, record_path, *[p for p in real_paths if p.exists()]):
        manifest["inputs"][str(p.relative_to(ROOT))] = hashlib.sha256(p.read_bytes()).hexdigest()
    for p in sorted(FIGURES.glob("fig*.*")):
        manifest["figures"][p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
    (EVIDENCE / "figure-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Exported figures and evidence to {SUBPROJECT}")


if __name__ == "__main__":
    main()
