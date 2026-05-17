"""PDF report generation untuk ScenarioRunResult — via ReportLab."""
from __future__ import annotations

import io
import re
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ─────────────────────────────────────────────────────────────────────────────
# Styles
# ─────────────────────────────────────────────────────────────────────────────


def _make_styles():
    base = getSampleStyleSheet()
    styles = {}
    styles["title"] = ParagraphStyle(
        "title", parent=base["Title"], fontSize=22, spaceAfter=20,
        textColor=colors.HexColor("#1e3a8a"),
    )
    styles["h1"] = ParagraphStyle(
        "h1", parent=base["Heading1"], fontSize=16, spaceBefore=18, spaceAfter=10,
        textColor=colors.HexColor("#1e3a8a"),
    )
    styles["h2"] = ParagraphStyle(
        "h2", parent=base["Heading2"], fontSize=13, spaceBefore=12, spaceAfter=6,
        textColor=colors.HexColor("#374151"),
    )
    styles["body"] = ParagraphStyle(
        "body", parent=base["BodyText"], fontSize=10, leading=14, spaceAfter=6,
    )
    styles["caption"] = ParagraphStyle(
        "caption", parent=base["BodyText"], fontSize=8, leading=11,
        textColor=colors.HexColor("#6b7280"),
    )
    styles["meta"] = ParagraphStyle(
        "meta", parent=base["BodyText"], fontSize=9, leading=12,
        textColor=colors.HexColor("#4b5563"),
    )
    styles["mono"] = ParagraphStyle(
        "mono", parent=base["BodyText"], fontSize=8, leading=11,
        fontName="Courier",
    )
    return styles


# ─────────────────────────────────────────────────────────────────────────────
# Markdown-ish → reportlab markup
# ─────────────────────────────────────────────────────────────────────────────


def _md_to_rl(text: str) -> str:
    """Translate basic markdown ke ReportLab inline markup."""
    if not text:
        return ""
    # Escape XML-special chars first
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    # Bold **x** atau __x__
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"__(.+?)__", r"<b>\1</b>", text)
    # Italic *x* atau _x_
    text = re.sub(r"(?<![*\w])\*([^*\n]+?)\*(?!\w)", r"<i>\1</i>", text)
    # Inline code `x`
    text = re.sub(r"`([^`]+)`", r"<font name='Courier'>\1</font>", text)
    return text


def _safe_paragraph(text: str, style) -> Paragraph:
    """Build a Paragraph, falling back to plain-escaped text if markup parse fails."""
    try:
        return Paragraph(text, style)
    except Exception:
        # Strip any tags + re-escape — last resort
        safe = re.sub(r"<[^>]+>", "", text)
        safe = safe.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        try:
            return Paragraph(safe, style)
        except Exception:
            return Paragraph("[content unrenderable]", style)


def _split_paragraphs(text: str, styles) -> list:
    """Split text by double-newline + bullet handling, return Paragraph flowables."""
    if not text:
        return []
    blocks = []
    paragraphs = text.split("\n\n")
    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        if p.startswith("### "):
            blocks.append(_safe_paragraph(_md_to_rl(p[4:]), styles["h2"]))
        elif p.startswith("## "):
            blocks.append(_safe_paragraph(_md_to_rl(p[3:]), styles["h2"]))
        elif p.startswith("# "):
            blocks.append(_safe_paragraph(_md_to_rl(p[2:]), styles["h1"]))
        else:
            lines = p.split("\n")
            cur_lines: list[str] = []
            for line in lines:
                if line.lstrip().startswith(("- ", "* ", "• ")):
                    if cur_lines:
                        blocks.append(_safe_paragraph(_md_to_rl(" ".join(cur_lines)), styles["body"]))
                        cur_lines = []
                    bullet_text = line.lstrip()[2:].strip()
                    blocks.append(_safe_paragraph(
                        f"• {_md_to_rl(bullet_text)}",
                        ParagraphStyle("bullet", parent=styles["body"], leftIndent=15),
                    ))
                else:
                    cur_lines.append(line)
            if cur_lines:
                blocks.append(_safe_paragraph(_md_to_rl(" ".join(cur_lines)), styles["body"]))
    return blocks


# ─────────────────────────────────────────────────────────────────────────────
# Main entry
# ─────────────────────────────────────────────────────────────────────────────


def generate_scenario_report(result, include_tool_outputs: bool = False) -> bytes:
    """Generate PDF report dari ScenarioRunResult. Returns PDF bytes."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title=f"WEF-Agentic Report — {result.scenario.get('name', 'Unnamed')}",
        author="WEF-Agentic Framework",
    )
    styles = _make_styles()
    story = []

    # ── Cover ────────────────────────────────────────────────────────────────
    story.append(Paragraph("WEF-Agentic", styles["title"]))
    story.append(Paragraph(
        "Function-based agentic AI framework untuk sub-national Water-Energy-Food "
        "Nexus governance — operasionalisasi WEF (2026a) & WEF (2026b).",
        styles["caption"],
    ))
    story.append(Spacer(1, 0.5 * cm))

    scenario = result.scenario
    location = {}
    for t in (result.water.tool_outputs or []):
        data = t.get("data", {})
        if isinstance(data, dict) and "location" in data:
            location = data["location"]
            break

    # Metadata table
    meta_data = [
        ["Scenario", scenario.get("name", "Unnamed")],
        ["Location", f"{location.get('name', '')} ({location.get('country', '')})"],
        ["Coordinates", f"lat={location.get('lat', 0):.3f}, lon={location.get('lon', 0):.3f}"],
        ["Policy", scenario.get("policy", "")],
        ["Horizon", str(scenario.get("horizon", ""))],
        ["Climate delta",
         f"P {scenario.get('delta_precip_pct', 0):+.1f}%, T {scenario.get('delta_temp_c', 0):+.1f}°C"],
        ["Generated", datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
    ]
    meta_table = Table(meta_data, colWidths=[4 * cm, 12 * cm])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f3f4f6")),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#374151")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 0.5 * cm))

    # Bounded autonomy notice
    story.append(Paragraph(
        "<b>⚠ ADVISORY ONLY:</b> Framework ini menarget functions di area "
        "<i>low-readiness</i> per WEF (2026a) — #43 Policy forecasting, #55 Policy "
        "impact prediction. Semua rekomendasi WAJIB di-review oleh analis manusia "
        "sebelum digunakan untuk decision-making.",
        styles["meta"],
    ))

    # ── Build all charts via matplotlib (reliable, no Chrome) ───────────────
    charts_png: dict[str, bytes | None] = {}
    try:
        from wef_agentic.reporting.pdf_charts import build_all_pngs
        charts_png = build_all_pngs(result)
    except Exception:
        charts_png = {}

    def _add_chart(key: str):
        png = charts_png.get(key)
        if png:
            try:
                img = Image(io.BytesIO(png), width=16 * cm, height=9 * cm)
                story.append(Spacer(1, 0.3 * cm))
                story.append(img)
                story.append(Spacer(1, 0.3 * cm))
            except Exception:
                pass

    # ── Coordinator synthesis ────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("1. Coordinator Synthesis", styles["h1"]))
    story.append(Paragraph(
        f"Provider: {result.coordinator.provider} | Model: {result.coordinator.model}",
        styles["caption"],
    ))
    story.extend(_split_paragraphs(result.coordinator.content, styles))
    _add_chart("coordinator")

    # ── Critic audit ─────────────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("2. Critic Audit", styles["h1"]))
    story.append(Paragraph(
        f"Provider: {result.critic.provider} | Model: {result.critic.model}",
        styles["caption"],
    ))
    story.extend(_split_paragraphs(result.critic.content, styles))
    _add_chart("critic")

    # ── Per-agent outputs ────────────────────────────────────────────────────
    for label, output, num, chart_key in [
        ("Water Agent", result.water, "3", "water"),
        ("Energy Agent", result.energy, "4", "energy"),
        ("Food Agent", result.food, "5", "food"),
    ]:
        story.append(PageBreak())
        story.append(Paragraph(f"{num}. {label}", styles["h1"]))
        story.append(Paragraph(
            f"Provider: {output.provider} | Model: {output.model} | "
            f"Tokens: in={output.usage_input_tokens}, out={output.usage_output_tokens}",
            styles["caption"],
        ))
        story.extend(_split_paragraphs(output.content, styles))
        _add_chart(chart_key)

        if include_tool_outputs and output.tool_outputs:
            story.append(Spacer(1, 0.3 * cm))
            story.append(Paragraph("Tool outputs (audit trail):", styles["h2"]))
            for t in output.tool_outputs:
                story.append(Paragraph(
                    f"<b>{t['tool']}</b>", styles["meta"],
                ))
                preview = str(t["data"])[:500]
                story.append(_safe_paragraph(_md_to_rl(preview), styles["mono"]))
                story.append(Spacer(1, 0.2 * cm))

    # ── Nexus footprint ──────────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("6. Nexus Footprint (operasionalisasi WEF 2026b)", styles["h1"]))
    est = result.footprint.estimate()
    fp_data = [
        ["Metric", "Value", "Note"],
        ["Total tokens", f"{est['total_tokens']:,}", "Sum input + output across all agents"],
        ["Energy (kWh)", f"{est['energy_kwh']:.4f}",
         "Proxy: 0.0003 kWh / 1k tokens (public estimate)"],
        ["Water (L)", f"{est['water_l']:.4f}", "Proxy: Zhang et al. (2025)"],
        ["CO₂eq (kg)", f"{est['co2_kg']:.4f}", "kWh × 0.4 (US grid mix avg)"],
    ]
    fp_table = Table(fp_data, colWidths=[3.5 * cm, 3 * cm, 9 * cm])
    fp_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 1), (1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(fp_table)
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(
        "<b>Per-agent breakdown:</b>", styles["body"],
    ))
    by_agent = result.footprint.by_agent()
    by_agent_data = [["Agent", "Tokens"]] + [
        [agent, f"{tokens:,}"] for agent, tokens in by_agent.items()
    ]
    by_agent_table = Table(by_agent_data, colWidths=[5 * cm, 4 * cm])
    by_agent_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3f4f6")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 1), (1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
    ]))
    story.append(by_agent_table)

    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(
        "<i>Honest caveat:</i> Footprint estimate adalah <i>order-of-magnitude</i> proxy, "
        "bukan measurement. Anthropic/Ollama tidak mempublikasikan data center-level "
        "intensity per request. Konstanta konversi di <font name='Courier'>config/llm.yaml → footprint:</font>.",
        styles["caption"],
    ))

    # ── References ───────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph("7. References", styles["h1"]))
    refs = [
        "WEF &amp; Capgemini (2026). <i>Making Agentic AI Work for Government: A Readiness "
        "Framework.</i> Insight Report, April 2026.",
        "WEF (2026). <i>Building Resilient and Scalable AI Value Chains: A Nexus Strategy.</i> "
        "Insight Report, May 2026.",
        "Zhang, Q. et al. (2025). <i>Making AI less &quot;thirsty&quot;: Uncovering and addressing the "
        "secret water footprint of AI models.</i> arXiv:2304.03271.",
        "Thornthwaite, C.W. &amp; Mather, J.R. (1957). Instructions and tables for computing "
        "potential evapotranspiration and the water balance.",
        "Doorenbos, J. &amp; Kassam, A.H. (1979). <i>Yield response to water.</i> FAO Irrigation "
        "and Drainage Paper 33.",
    ]
    for r in refs:
        story.append(Paragraph(f"• {r}", styles["body"]))

    # Build
    doc.build(story)
    buf.seek(0)
    return buf.read()
