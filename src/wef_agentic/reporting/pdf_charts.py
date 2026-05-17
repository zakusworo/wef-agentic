"""Matplotlib chart renderers untuk PDF embedding (reliable, no Chrome).

Plotly versions di charts.py untuk Streamlit UI interaktif.
"""
from __future__ import annotations

import io
import re

import matplotlib

matplotlib.use("Agg")  # non-interactive backend untuk PDF gen di server
import matplotlib.pyplot as plt
import numpy as np

from wef_agentic.reporting.charts import (
    CRITIC_MARKERS,
    PALETTE,
    _find_tool_output,
)


def _save_png(fig) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def water_png(agent_output) -> bytes | None:
    data = _find_tool_output(agent_output.tool_outputs, "run_water_balance")
    if not data or "monthly" not in data or not data["monthly"]:
        return None

    monthly = data["monthly"]
    month_labels = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun",
                    "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
    labels = [month_labels[m["month"] - 1] for m in monthly]
    precip = [m["precip_mm"] for m in monthly]
    et0 = [m["et0_mm"] for m in monthly]
    surplus = [m["surplus_mm"] for m in monthly]
    deficit = [m["deficit_mm"] for m in monthly]
    soil = [m.get("soil_moisture_mm", 0) for m in monthly]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 5),
                                    gridspec_kw={"height_ratios": [2, 1]})
    x = np.arange(len(labels))
    width = 0.35

    ax1.bar(x - width/2, precip, width, label="Hujan (mm)",
            color=PALETTE["water"], alpha=0.85)
    ax1.bar(x + width/2, et0, width, label="ET₀ (mm)", color="#f97316", alpha=0.7)
    ax1.plot(x, surplus, "o-", label="Surplus", color=PALETTE["surplus"], linewidth=2)
    ax1.plot(x, deficit, "s--", label="Defisit", color=PALETTE["deficit"], linewidth=2)
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels)
    ax1.set_ylabel("mm")
    ax1.set_title(f"Water Balance — {data.get('station', '')} ({data.get('year', '')})",
                  color=PALETTE["primary"], fontsize=11, fontweight="bold")
    ax1.legend(loc="upper right", fontsize=8, ncol=2)
    ax1.grid(axis="y", alpha=0.3)

    ax2.fill_between(x, soil, alpha=0.3, color=PALETTE["water"])
    ax2.plot(x, soil, color=PALETTE["water"], linewidth=2)
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels)
    ax2.set_ylabel("mm")
    ax2.set_title("Soil Moisture", fontsize=9)
    ax2.grid(alpha=0.3)

    fig.tight_layout()
    return _save_png(fig)


def energy_png(agent_output) -> bytes | None:
    data = _find_tool_output(agent_output.tool_outputs, "project_energy_demand")
    if not data or "yearly_summary" not in data or not data["yearly_summary"]:
        return None

    yearly = data["yearly_summary"]
    years = [r["year"] for r in yearly]
    demand = [r["demand_total_gwh"] for r in yearly]
    ep = data.get("endpoints", {})

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(years, demand, "o-", color=PALETTE["energy"], linewidth=2.5, markersize=8)
    ax.fill_between(years, demand, alpha=0.15, color=PALETTE["energy"])

    for yr_target in (2030, 2050):
        key = f"demand_{yr_target}_gwh"
        if ep.get(key) is not None:
            ax.annotate(f"{yr_target}: {ep[key]:.0f} GWh",
                        xy=(yr_target, ep[key]),
                        xytext=(10, 20), textcoords="offset points",
                        bbox=dict(boxstyle="round,pad=0.3", fc="white", ec=PALETTE["primary"]),
                        fontsize=9, color=PALETTE["primary"], fontweight="bold",
                        arrowprops=dict(arrowstyle="->", color=PALETTE["primary"]))

    loc_name = data.get("location", {}).get("name", "")
    quality = data.get("data_quality", "")
    ax.set_title(f"Proyeksi Demand Listrik — {loc_name}\n[{quality}]",
                 color=PALETTE["primary"], fontsize=11, fontweight="bold")
    ax.set_xlabel("Tahun")
    ax.set_ylabel("Demand (GWh/year)")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    return _save_png(fig)


def food_png(agent_output) -> bytes | None:
    data = _find_tool_output(agent_output.tool_outputs, "project_crop_yield")
    if not data or "yearly_summary" not in data or not data["yearly_summary"]:
        return None

    yearly = data["yearly_summary"]
    years = [r["year"] for r in yearly]
    area = [r.get("area_ha", 0) for r in yearly]
    yield_th = [r.get("yield_t_ha", 0) for r in yearly]
    production = [r.get("production_t", 0) for r in yearly]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))

    ax1.plot(years, area, "o-", color="#0ea5e9", linewidth=2, label="Luas (ha)")
    ax1.set_ylabel("Luas (ha)", color="#0ea5e9")
    ax1.tick_params(axis="y", labelcolor="#0ea5e9")
    ax1.set_xlabel("Tahun")
    ax1.grid(alpha=0.3)

    ax1b = ax1.twinx()
    ax1b.plot(years, yield_th, "s--", color="#84cc16", linewidth=2, label="Yield (t/ha)")
    ax1b.set_ylabel("Yield (t/ha)", color="#84cc16")
    ax1b.tick_params(axis="y", labelcolor="#84cc16")

    ax2.bar(years, production, color=PALETTE["food"], alpha=0.8)
    ax2.set_xlabel("Tahun")
    ax2.set_ylabel("Produksi (ton)")
    ax2.grid(axis="y", alpha=0.3)

    crop = data.get("crop", "padi")
    loc_name = data.get("location", {}).get("name", "")
    quality = data.get("data_quality", "")
    fig.suptitle(f"Proyeksi Pangan ({crop.title()}) — {loc_name}\n[{quality}]",
                 color=PALETTE["primary"], fontsize=11, fontweight="bold")
    fig.tight_layout()
    return _save_png(fig)


def critic_png(agent_output) -> bytes | None:
    content = agent_output.content or ""
    counts = {}
    for marker, (label, _color) in CRITIC_MARKERS.items():
        n = content.count(marker)
        if marker == "✓":
            n += len(re.findall(r"\bKONSISTEN\b", content, re.IGNORECASE))
        elif marker == "⚠":
            n += len(re.findall(r"\bINKONSISTEN\b", content, re.IGNORECASE))
        elif marker == "⚙":
            n += len(re.findall(r"\bMISSING\b", content, re.IGNORECASE))
        elif marker == "🚩":
            n += len(re.findall(r"\bERROR\s+CONSEQUENCE\b|\bERROR-HIGH\b", content, re.IGNORECASE))
        if n > 0:
            counts[label] = n

    if not counts:
        return None

    labels = list(counts.keys())
    values = list(counts.values())
    colors = [next((c for _m, (lbl, c) in CRITIC_MARKERS.items() if lbl == lab), PALETTE["neutral"])
              for lab in labels]

    fig, ax = plt.subplots(figsize=(6, 5))
    _wedges, _texts, _autotexts = ax.pie(
        values, labels=labels, colors=colors, autopct="%d",
        startangle=90, wedgeprops=dict(width=0.45, edgecolor="white", linewidth=2),
        textprops=dict(fontsize=10),
    )
    ax.text(0, 0, f"Total\n{sum(values)}", ha="center", va="center",
            fontsize=14, fontweight="bold")
    ax.set_title("Critic Audit — Distribusi Findings",
                 color=PALETTE["primary"], fontsize=11, fontweight="bold")
    fig.tight_layout()
    return _save_png(fig)


def coordinator_png(result) -> bytes | None:
    by_agent = result.footprint.by_agent()
    if not by_agent:
        return None

    agents = list(by_agent.keys())
    tokens = list(by_agent.values())
    agent_colors = {
        "water": PALETTE["water"], "energy": PALETTE["energy"],
        "food": PALETTE["food"], "critic": PALETTE["critic"],
        "coordinator": PALETTE["primary"],
    }
    colors = [agent_colors.get(a, PALETTE["neutral"]) for a in agents]

    fig, ax = plt.subplots(figsize=(8, 4))
    bars = ax.bar(agents, tokens, color=colors, alpha=0.9)
    for bar, t in zip(bars, tokens, strict=True):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(tokens)*0.01,
                f"{t:,}", ha="center", fontsize=9)
    ax.set_title("Token Usage per Agent",
                 color=PALETTE["primary"], fontsize=11, fontweight="bold")
    ax.set_ylabel("Tokens")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    return _save_png(fig)


def build_all_pngs(result) -> dict[str, bytes | None]:
    """Render semua charts ke PNG bytes via matplotlib."""
    return {
        "water": water_png(result.water),
        "energy": energy_png(result.energy),
        "food": food_png(result.food),
        "critic": critic_png(result.critic),
        "coordinator": coordinator_png(result),
    }
