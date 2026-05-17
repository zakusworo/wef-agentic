"""Chart generators per agent — Plotly untuk UI + PNG bytes untuk PDF."""
from __future__ import annotations

import re
from typing import Any

import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

PALETTE = {
    "primary": "#1e3a8a",
    "water": "#3b82f6",
    "energy": "#f59e0b",
    "food": "#10b981",
    "critic": "#8b5cf6",
    "deficit": "#ef4444",
    "surplus": "#22c55e",
    "neutral": "#6b7280",
}


def _find_tool_output(tool_outputs: list[dict], tool_name: str) -> dict | None:
    """Cari tool output by name."""
    for t in tool_outputs or []:
        if t.get("tool") == tool_name:
            return t.get("data")
    return None


def fig_to_png_bytes(fig: go.Figure, width: int = 800, height: int = 450) -> bytes | None:
    """Export figure ke PNG bytes. Returns None jika kaleido tidak tersedia."""
    try:
        return fig.to_image(format="png", width=width, height=height, scale=2)
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Water Agent charts
# ─────────────────────────────────────────────────────────────────────────────


def water_chart(agent_output) -> go.Figure | None:
    """Monthly water balance: precip vs ET0 bars + surplus/deficit overlay."""
    data = _find_tool_output(agent_output.tool_outputs, "run_water_balance")
    if not data or "monthly" not in data:
        return None

    monthly = data["monthly"]
    if not monthly:
        return None

    months = [m["month"] for m in monthly]
    month_labels = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun",
                    "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
    labels = [month_labels[m - 1] for m in months]
    precip = [m["precip_mm"] for m in monthly]
    et0 = [m["et0_mm"] for m in monthly]
    surplus = [m["surplus_mm"] for m in monthly]
    deficit = [m["deficit_mm"] for m in monthly]
    soil_moisture = [m.get("soil_moisture_mm", 0) for m in monthly]

    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=("Bulanan: Hujan vs Evapotranspirasi vs Surplus/Defisit",
                        "Kelembaban Tanah (Soil Moisture)"),
        vertical_spacing=0.15,
        row_heights=[0.65, 0.35],
    )

    # Top: bars for P, ET0 + line for surplus/deficit
    fig.add_trace(
        go.Bar(x=labels, y=precip, name="Hujan (mm)", marker_color=PALETTE["water"], opacity=0.85),
        row=1, col=1,
    )
    fig.add_trace(
        go.Bar(x=labels, y=et0, name="ET₀ (mm)", marker_color="#f97316", opacity=0.7),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(x=labels, y=surplus, mode="lines+markers", name="Surplus",
                   line=dict(color=PALETTE["surplus"], width=3), marker=dict(size=8)),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(x=labels, y=deficit, mode="lines+markers", name="Defisit",
                   line=dict(color=PALETTE["deficit"], width=3, dash="dash"), marker=dict(size=8)),
        row=1, col=1,
    )

    # Bottom: soil moisture area
    fig.add_trace(
        go.Scatter(x=labels, y=soil_moisture, mode="lines", name="Soil Moisture",
                   fill="tozeroy", line=dict(color=PALETTE["water"], width=2),
                   fillcolor="rgba(59, 130, 246, 0.2)", showlegend=False),
        row=2, col=1,
    )

    fig.update_yaxes(title_text="mm", row=1, col=1)
    fig.update_yaxes(title_text="mm", row=2, col=1)
    fig.update_layout(
        height=550,
        barmode="group",
        title=dict(text=f"💧 Water Balance — Station: {data.get('station', 'N/A')} ({data.get('year', '')})",
                   font=dict(size=14, color=PALETTE["primary"])),
        margin=dict(l=50, r=20, t=80, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# Energy Agent charts
# ─────────────────────────────────────────────────────────────────────────────


def energy_chart(agent_output) -> go.Figure | None:
    """Yearly demand projection + endpoint markers + breakdown stacked."""
    data = _find_tool_output(agent_output.tool_outputs, "project_energy_demand")
    if not data or "yearly_summary" not in data:
        return None

    yearly = data["yearly_summary"]
    if not yearly:
        return None

    years = [r["year"] for r in yearly]
    demand = [r["demand_total_gwh"] for r in yearly]

    # Endpoints from data
    ep = data.get("endpoints", {})
    d_2030 = ep.get("demand_2030_gwh")
    d_2050 = ep.get("demand_2050_gwh")

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(x=years, y=demand, mode="lines+markers",
                   name=f"Demand ({data.get('scenario', '')})",
                   line=dict(color=PALETTE["energy"], width=3),
                   marker=dict(size=10),
                   fill="tozeroy", fillcolor="rgba(245, 158, 11, 0.15)"),
    )

    if d_2030 is not None:
        fig.add_annotation(x=2030, y=d_2030,
                           text=f"<b>2030: {d_2030:.0f} GWh</b>",
                           showarrow=True, arrowhead=2, arrowcolor=PALETTE["primary"],
                           bgcolor="white", bordercolor=PALETTE["primary"], borderwidth=1,
                           ax=0, ay=-40)
    if d_2050 is not None:
        fig.add_annotation(x=2050, y=d_2050,
                           text=f"<b>2050: {d_2050:.0f} GWh</b>",
                           showarrow=True, arrowhead=2, arrowcolor=PALETTE["primary"],
                           bgcolor="white", bordercolor=PALETTE["primary"], borderwidth=1,
                           ax=0, ay=-40)

    loc_name = data.get("location", {}).get("name", "")
    quality = data.get("data_quality", "")
    fig.update_layout(
        height=400,
        title=dict(text=f"⚡ Proyeksi Demand Listrik — {loc_name}<br>"
                        f"<sub style='color:gray'>{quality}</sub>",
                   font=dict(size=14, color=PALETTE["primary"])),
        xaxis_title="Tahun",
        yaxis_title="Demand (GWh/year)",
        margin=dict(l=50, r=20, t=80, b=40),
        hovermode="x unified",
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# Food Agent charts
# ─────────────────────────────────────────────────────────────────────────────


def food_chart(agent_output) -> go.Figure | None:
    """Area + yield + production trends."""
    data = _find_tool_output(agent_output.tool_outputs, "project_crop_yield")
    if not data or "yearly_summary" not in data:
        return None

    yearly = data["yearly_summary"]
    if not yearly:
        return None

    years = [r["year"] for r in yearly]
    area = [r.get("area_ha", 0) for r in yearly]
    yield_th = [r.get("yield_t_ha", 0) for r in yearly]
    production = [r.get("production_t", 0) for r in yearly]

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=("Luas Panen + Produktivitas", "Total Produksi"),
        specs=[[{"secondary_y": True}, {"secondary_y": False}]],
        column_widths=[0.5, 0.5],
    )

    fig.add_trace(
        go.Scatter(x=years, y=area, name="Luas (ha)", mode="lines+markers",
                   line=dict(color="#0ea5e9", width=2)),
        row=1, col=1, secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(x=years, y=yield_th, name="Yield (t/ha)", mode="lines+markers",
                   line=dict(color="#84cc16", width=2, dash="dash")),
        row=1, col=1, secondary_y=True,
    )

    fig.add_trace(
        go.Bar(x=years, y=production, name="Produksi (ton)",
               marker_color=PALETTE["food"], opacity=0.8),
        row=1, col=2,
    )

    crop = data.get("crop", "padi")
    loc_name = data.get("location", {}).get("name", "")
    quality = data.get("data_quality", "")
    fig.update_xaxes(title_text="Tahun", row=1, col=1)
    fig.update_xaxes(title_text="Tahun", row=1, col=2)
    fig.update_yaxes(title_text="Luas (ha)", row=1, col=1, secondary_y=False)
    fig.update_yaxes(title_text="Yield (t/ha)", row=1, col=1, secondary_y=True)
    fig.update_yaxes(title_text="Produksi (ton)", row=1, col=2)
    fig.update_layout(
        height=400,
        title=dict(text=f"🌾 Proyeksi Pangan ({crop.title()}) — {loc_name}<br>"
                        f"<sub style='color:gray'>{quality}</sub>",
                   font=dict(size=14, color=PALETTE["primary"])),
        margin=dict(l=50, r=20, t=80, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# Critic Agent chart
# ─────────────────────────────────────────────────────────────────────────────


CRITIC_MARKERS = {
    "✓": ("KONSISTEN", PALETTE["surplus"]),
    "⚠": ("INKONSISTEN", "#f59e0b"),
    "⚙": ("MISSING", "#6b7280"),
    "🚩": ("ERROR-HIGH", PALETTE["deficit"]),
}


def critic_chart(agent_output) -> go.Figure | None:
    """Donut chart: hitung occurrence audit markers di content."""
    content = agent_output.content or ""
    counts = {}
    for marker, (label, _color) in CRITIC_MARKERS.items():
        # Count both raw marker and alternative ASCII versions
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
        # Fallback: jika tidak ada marker dikenali, parse heuristik
        counts = {"NEUTRAL": 1}

    labels = list(counts.keys())
    values = list(counts.values())
    colors = [next((c for _m, (lbl, c) in CRITIC_MARKERS.items() if lbl == lab), PALETTE["neutral"])
              for lab in labels]

    fig = go.Figure(
        data=[go.Pie(
            labels=labels, values=values,
            hole=0.55,
            marker=dict(colors=colors, line=dict(color="white", width=2)),
            textinfo="label+value",
            textfont=dict(size=12),
        )]
    )
    fig.update_layout(
        height=350,
        title=dict(text="🔍 Critic Audit — Distribusi Findings",
                   font=dict(size=14, color=PALETTE["primary"])),
        margin=dict(l=20, r=20, t=60, b=20),
        annotations=[dict(text=f"Total<br><b>{sum(values)}</b>",
                          x=0.5, y=0.5, font_size=14, showarrow=False)],
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# Coordinator chart (footprint + cross-sector summary)
# ─────────────────────────────────────────────────────────────────────────────


def coordinator_chart(result) -> go.Figure | None:
    """Token usage per agent — bar chart (re-use of footprint)."""
    by_agent = result.footprint.by_agent()
    if not by_agent:
        return None

    agents = list(by_agent.keys())
    tokens = list(by_agent.values())
    agent_colors = {
        "water": PALETTE["water"],
        "energy": PALETTE["energy"],
        "food": PALETTE["food"],
        "critic": PALETTE["critic"],
        "coordinator": PALETTE["primary"],
    }
    colors = [agent_colors.get(a, PALETTE["neutral"]) for a in agents]

    fig = go.Figure(
        data=[go.Bar(
            x=agents, y=tokens,
            marker_color=colors,
            text=[f"{t:,}" for t in tokens],
            textposition="outside",
        )]
    )
    fig.update_layout(
        height=350,
        title=dict(text="🧭 Token Usage per Agent",
                   font=dict(size=14, color=PALETTE["primary"])),
        yaxis_title="Tokens",
        margin=dict(l=50, r=20, t=60, b=40),
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# Convenience: chart-per-agent builder
# ─────────────────────────────────────────────────────────────────────────────


def build_all_charts(result) -> dict[str, Any]:
    """Build dict {agent_name: plotly_figure}."""
    return {
        "water": water_chart(result.water),
        "energy": energy_chart(result.energy),
        "food": food_chart(result.food),
        "critic": critic_chart(result.critic),
        "coordinator": coordinator_chart(result),
    }
