"""WEF-Agentic Streamlit UI — multi-city WEF Nexus governance dengan agentic AI."""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from wef_agentic.config.settings import settings  # noqa: E402
from wef_agentic.data.sources import (  # noqa: E402
    fetch_all_for_location,
    manual_override_schema,
)
from wef_agentic.geo import (  # noqa: E402
    geocode,
    get_preset,
    list_presets,
)
from wef_agentic.orchestration import (  # noqa: E402
    SCENARIOS,
    get_scenario,
    run_scenario,
)
from wef_agentic.reporting import (  # noqa: E402
    coordinator_chart,
    critic_chart,
    energy_chart,
    food_chart,
    generate_scenario_report,
    water_chart,
)

st.set_page_config(
    page_title="WEF-Agentic",
    page_icon=":droplet:",
    layout="wide",
)


# ─────────────────────────────────────────────────────────────────────────────
# Session state init
# ─────────────────────────────────────────────────────────────────────────────

if "resolved_location" not in st.session_state:
    st.session_state.resolved_location = get_preset("sleman")
if "results_history" not in st.session_state:
    # dict key = f"{scenario_id}__{location_slug}"
    st.session_state.results_history = {}
if "last_result" not in st.session_state:
    st.session_state.last_result = None

demo_mode = os.environ.get("WEF_AGENTIC_DEMO") == "1"
if demo_mode and "demo_loaded" not in st.session_state:
    from wef_agentic.ui.demo import load_demo

    demo_result = load_demo()
    st.session_state.last_result = demo_result
    st.session_state.results_history["S2_JETP_Aligned__sleman"] = demo_result
    st.session_state.demo_loaded = True


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────

st.sidebar.title("WEF-Agentic")
st.sidebar.caption(
    "Function-based agentic AI untuk multi-city WEF Nexus governance — "
    "operasionalisasi WEF (2026a) & WEF (2026b)."
)

with st.sidebar:
    st.subheader("📍 Lokasi")
    location_mode = st.radio(
        "Mode",
        options=["Preset", "Custom city"],
        index=0,
        horizontal=True,
    )

    if location_mode == "Preset":
        presets = list_presets()
        preset_key = st.selectbox(
            "Preset", options=[p.name for p in presets], index=0,
        )
        st.session_state.resolved_location = get_preset(preset_key.lower())
    else:
        city_input = st.text_input(
            "Nama kota/wilayah", value="",
            placeholder="cth: Bandung, Marrakesh, Nairobi...",
        )
        if st.button("🔍 Resolve", width="stretch"):
            if city_input.strip():
                with st.spinner(f"Mencari '{city_input}'..."):
                    try:
                        results = geocode(city_input, count=5)
                    except Exception as e:
                        st.error(f"Geocoding gagal: {e}")
                        results = []
                if results:
                    st.session_state.geocode_results = results
                    st.session_state.resolved_location = results[0]
                else:
                    st.warning(f"Tidak ditemukan: '{city_input}'")

        if "geocode_results" in st.session_state and st.session_state.geocode_results:
            choices = st.session_state.geocode_results
            if len(choices) > 1:
                names = [f"{r.display} (pop={r.population or 'n/a'})" for r in choices]
                idx = st.radio(
                    "Pilih match:",
                    options=list(range(len(names))),
                    format_func=lambda i: names[i],
                    index=0,
                )
                st.session_state.resolved_location = choices[idx]

    loc = st.session_state.resolved_location
    if loc is not None:
        with st.container(border=True):
            st.markdown(f"**{loc.display}**")
            st.caption(
                f"📍 lat={loc.lat:.3f}, lon={loc.lon:.3f}  \n"
                f"🌐 {loc.country_code} • TZ: {loc.timezone}  \n"
                f"👥 pop: {f'{loc.population:,}' if loc.population else 'unknown'}  \n"
                f"🏷 source: {loc.source}"
            )

    st.divider()

    st.subheader("🤖 Provider LLM")
    provider_choice = st.selectbox(
        "Provider",
        options=["ollama-local", "ollama-cloud", "claude-agent-sdk"],
        index=2 if demo_mode else 0,
        help="Override semua agen. ollama-cloud butuh OLLAMA_API_KEY di .env.",
    )
    os.environ["WEF_AGENTIC_PROVIDER_OVERRIDE"] = provider_choice

    if provider_choice == "ollama-local":
        model_choice = st.selectbox(
            "Model lokal", options=["gemma4:e4b", "llama3.2:1b"], index=0,
        )
        os.environ["WEF_AGENTIC_MODEL_OVERRIDE"] = model_choice
    elif provider_choice == "ollama-cloud":
        model_choice = st.selectbox(
            "Model cloud", options=["deepseek-v4-pro:cloud", "glm-5.3-flash:cloud"], index=0,
        )
        os.environ["WEF_AGENTIC_MODEL_OVERRIDE"] = model_choice
        if not (os.environ.get("OLLAMA_API_KEY") or settings.ollama_api_key):
            st.warning("⚠ OLLAMA_API_KEY belum di-set di `.env`")
    else:
        os.environ.pop("WEF_AGENTIC_MODEL_OVERRIDE", None)
        st.caption("Claude Code subscription (no key)")

    st.divider()

    st.subheader("📋 Skenario")
    scenario_id = st.radio(
        "Pilih skenario",
        options=list(SCENARIOS.keys()),
        format_func=lambda k: SCENARIOS[k]["name"],
        index=1 if demo_mode else 0,
    )

    run_btn = st.button(
        "▶ Run Scenario", type="primary", width="stretch",
        disabled=(loc is None),
    )

    if st.session_state.results_history:
        if st.button(f"🗑 Clear history ({len(st.session_state.results_history)})",
                     width="stretch"):
            st.session_state.results_history = {}
            st.rerun()

    st.divider()
    st.caption(
        "⚠ **Bounded autonomy (WEF 2026a):** Output framework ADVISORY ONLY untuk "
        "low-readiness functions (#43, #55). Selalu review manusia."
    )


# ─────────────────────────────────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────────────────────────────────

st.title("WEF-Agentic: Multi-City WEF Nexus Framework")

scenario_data = get_scenario(scenario_id)
if st.session_state.resolved_location is not None:
    loc = st.session_state.resolved_location
    scenario_data["location_query"] = "sleman" if loc.has_local_data else loc.name


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _dashboard_cards(result):
    """Top-of-page summary cards from the deterministic nexus key figures."""
    k = result.nexus.key_figures()
    air, energi, pangan = k["air"], k["energi"], k["pangan"]

    cols = st.columns(5)
    cols[0].metric(
        "💧 Water deficit",
        f"{air['defisit_mm']:.0f} mm/yr",
        delta=f"stress {air['water_stress_setelah_irigasi']:.3f} (irigasi)",
        delta_color="off",
    )
    cols[1].metric(
        "⚡ Demand 2030", f"{energi['demand_2030_gwh'] or 0:.0f} GWh",
        delta=f"+{energi['tambahan_pompa_irigasi_akibat_iklim_gwh']:.2f} GWh pompa (iklim)",
        delta_color="off",
    )
    ssl = pangan.get("ssl_2030")
    if ssl is None:
        cols[2].metric("🌾 SSL padi", "n/a", help=pangan.get("alasan"))
    else:
        cols[2].metric(
            "🌾 SSL padi",
            f"{ssl:.2f}",
            delta="surplus" if ssl >= 1 else f"defisit {(1-ssl)*100:.0f}%",
            delta_color="normal" if ssl >= 1 else "inverse",
        )
    cols[3].metric("🌍 CO₂eq 2030", f"{energi['emisi_2030_mt_co2']:.2f} Mt")
    cols[4].metric("🤖 LLM tokens", f"{result.footprint.total_tokens:,}")


def _checks_panel(nexus):
    icon = {"ok": "🟢", "warn": "🟡", "fail": "🔴"}
    for w in nexus.warnings:
        st.warning(w)
    df = pd.DataFrame([
        {"": icon.get(c["status"], "⚪"), "Check": c["name"], "Detail": c["detail"]}
        for c in nexus.checks
    ])
    st.dataframe(df, width="stretch", hide_index=True)


def _footprint_panel(footprint):
    est = footprint.estimate()
    cols = st.columns(5)
    cols[0].metric("Total tokens", f"{est['total_tokens']:,}")
    cols[1].metric("⚡ Energy (kWh)", f"{est['energy_kwh']:.4f}")
    cols[2].metric("💧 Water on-site (L)", f"{est['water_onsite_l']:.4f}")
    cols[3].metric("💧 Water off-site (L)", f"{est['water_offsite_l']:.4f}")
    cols[4].metric("🌍 CO₂eq (kg)", f"{est['co2_kg']:.4f}")
    for note in est["notes"]:
        st.caption(f"⚠ {note}")
    st.dataframe(pd.DataFrame(est["per_entry"]), width="stretch", hide_index=True)

    by_agent = footprint.by_agent()
    if by_agent:
        df = pd.DataFrame(
            {"agent": list(by_agent.keys()), "tokens": list(by_agent.values())}
        )
        fig = px.bar(df, x="agent", y="tokens", title="Token usage per agent")
        st.plotly_chart(fig, width="stretch")


def _agent_card(label: str, output, icon: str = "", chart_fig=None):
    with st.expander(f"{icon} {label} — {output.provider} / {output.model}", expanded=False):
        st.markdown(output.content)
        if chart_fig is not None:
            st.divider()
            st.plotly_chart(chart_fig, width="stretch")
        if output.tool_outputs:
            st.divider()
            st.caption("**Tool outputs (audit trail):**")
            for t in output.tool_outputs:
                with st.expander(f"📦 {t['tool']}", expanded=False):
                    st.json(t["data"])


def _provenance_panel(location):
    """Show data sources status untuk location ini."""
    st.markdown(f"### 📊 Data Sources untuk {location.display}")
    st.caption(
        "Setiap variable yang dipakai agen diresolve dari source berbeda "
        "(Open-Meteo, World Bank, BPS Sleman, atau country proxy). "
        "Tier 1 = authoritative; Tier 3 = last-resort proxy. "
        "Override via JSON file di tab terbawah."
    )

    with st.spinner("Resolving all variables..."):
        try:
            results = fetch_all_for_location(location)
        except Exception as e:
            st.error(f"Gagal resolve: {e}")
            return

    rows = []
    for var, (packet, trace) in sorted(results.items()):
        if packet:
            tier_emoji = {1: "🟢", 2: "🟡", 3: "🔴"}.get(packet.tier, "⚪")
            rows.append({
                "Variable": var,
                "Value": f"{packet.value} {packet.unit}",
                "Source": packet.source,
                "Tier": f"{tier_emoji} T{packet.tier}",
                "Conf": f"{packet.confidence:.2f}",
                "Year": str(packet.year) if packet.year else "—",
                "Note": packet.note[:80] + ("..." if len(packet.note) > 80 else ""),
            })
        else:
            rows.append({
                "Variable": var, "Value": "—", "Source": "no source",
                "Tier": "⚫", "Conf": "—", "Year": "—",
                "Note": str(trace.attempts[-1]) if trace.attempts else "no attempts",
            })

    df = pd.DataFrame(rows)
    st.dataframe(df, width="stretch", hide_index=True)


def _comparison_panel():
    """Side-by-side comparison antar saved scenario runs."""
    if not st.session_state.results_history:
        st.info("Belum ada hasil disimpan. Jalankan scenario di tab **Run** dulu.")
        return

    options = list(st.session_state.results_history.keys())
    selected = st.multiselect(
        "Pilih 2-3 hasil untuk dibandingkan",
        options=options,
        default=options[:min(3, len(options))],
        max_selections=3,
    )

    if len(selected) < 2:
        st.info("Pilih minimal 2 hasil untuk comparison.")
        return

    results = [st.session_state.results_history[k] for k in selected]
    names = [r.scenario.get("name", k) for r, k in zip(results, selected, strict=True)]

    # ─── Metrics comparison ───
    metrics_data = []
    for name, r in zip(names, results, strict=True):
        k = r.nexus.key_figures()
        metrics_data.append({
            "Scenario": name,
            "Water deficit (mm)": k["air"]["defisit_mm"],
            "Water surplus (mm)": k["air"]["surplus_mm"],
            "Water stress": k["air"]["water_stress_setelah_irigasi"],
            "Demand 2030 (GWh)": k["energi"]["demand_2030_gwh"] or 0,
            "Demand horizon (GWh)": k["energi"]["demand_horizon_gwh"] or 0,
            "SSL padi": k["pangan"].get("ssl_2030") or 0,
            "CO₂eq Mt": k["energi"]["emisi_2030_mt_co2"],
            "Total tokens": r.footprint.total_tokens,
        })

    df_metrics = pd.DataFrame(metrics_data)
    st.subheader("📊 Comparison Metrics")
    st.dataframe(df_metrics, width="stretch", hide_index=True)

    # ─── Radar chart (normalized) ───
    st.subheader("🎯 Trade-off Radar Chart")
    radar_categories = ["Water security", "Energy efficiency", "Food security",
                        "Climate (low CO₂)", "Token efficiency"]
    fig = go.Figure()
    for _i, row in df_metrics.iterrows():
        # Normalize each metric to 0-1 (higher = better)
        max_def = max(r["Water deficit (mm)"] for r in metrics_data) or 1
        max_dem = max(r["Demand 2030 (GWh)"] for r in metrics_data) or 1
        max_co2 = max(r["CO₂eq Mt"] for r in metrics_data) or 1
        max_tok = max(r["Total tokens"] for r in metrics_data) or 1

        scores = [
            1 - row["Water deficit (mm)"] / max_def,
            1 - row["Demand 2030 (GWh)"] / (max_dem * 2),
            min(1.0, row["SSL padi"]),
            1 - row["CO₂eq Mt"] / max_co2,
            1 - row["Total tokens"] / (max_tok * 1.5),
        ]
        fig.add_trace(go.Scatterpolar(
            r=[*scores, scores[0]],
            theta=[*radar_categories, radar_categories[0]],
            fill="toself",
            name=row["Scenario"],
            opacity=0.5,
        ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
        showlegend=True, height=500,
    )
    st.plotly_chart(fig, width="stretch")

    # ─── Side-by-side coordinator synthesis ───
    st.subheader("🧭 Coordinator Synthesis per Scenario")
    cols = st.columns(len(results))
    for col, name, r in zip(cols, names, results, strict=True):
        with col:
            st.markdown(f"**{name}**")
            st.markdown(r.coordinator.content)


# ─────────────────────────────────────────────────────────────────────────────
# Main: Tabs
# ─────────────────────────────────────────────────────────────────────────────

tab_run, tab_compare, tab_data = st.tabs(
    ["▶ Run Scenario", "📊 Compare Scenarios", "🔬 Data Sources"]
)


# ═══════════════════════════════════════════════════════════════════════════
# TAB: Run Scenario
# ═══════════════════════════════════════════════════════════════════════════

with tab_run:
    if demo_mode:
        st.info("Demo: hasil Claude yang direkam dengan data iklim sintetis dan parameter belum "
                "dikalibrasi. Run Scenario menjalankan analisis baru melalui provider terpilih.")
    with st.expander("📋 Detail skenario + lokasi", expanded=False):
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("**Scenario:**")
            st.json({k: v for k, v in scenario_data.items() if k != "location_query"})
        with col_b:
            st.markdown("**Resolved location:**")
            if st.session_state.resolved_location:
                st.json(st.session_state.resolved_location.to_dict())

    if run_btn:
        loc = st.session_state.resolved_location
        if loc is None:
            st.error("Pilih lokasi terlebih dahulu.")
            st.stop()

        is_realtime = loc.source == "geocoded"

        with st.status(
            f"🚀 `{scenario_data['name']}` → **{loc.display}**...",
            expanded=True,
        ) as status:
            try:
                st.write(f"⚙ Provider: `{provider_choice}` | Mode: "
                         + ("realtime fetch" if is_realtime else "cached"))
                phase_labels = {
                    "nexus_start": "Phase 1/4 — 🔗 Nexus deterministik (data + model fisik)...",
                    "domain_start": "Phase 2/4 — 💧⚡🌾 Agen domain (paralel)...",
                    "critic_start": "Phase 3/4 — 🔍 Critic Agent...",
                    "coordinator_start": "Phase 4/4 — 🧭 Coordinator Agent...",
                }

                def on_event(phase, payload):
                    if phase in phase_labels:
                        status.update(label=phase_labels[phase])
                        st.write(f"**{phase_labels[phase]}**")
                        if phase == "nexus_start" and is_realtime:
                            st.write("   ⏱ Fetching Open-Meteo (~30-60s untuk lokasi baru)...")
                    elif phase == "nexus_done":
                        flagged = sum(c["status"] != "ok" for c in payload["checks"])
                        st.write(f"   ✓ done in {payload['elapsed']:.1f}s | "
                                 f"{len(payload['checks'])} checks, {flagged} warn/fail")
                    elif phase == "agent_done":
                        retry = (f" | ⟳ {payload['attempts']} attempts"
                                 if payload["attempts"] > 1 else "")
                        st.write(f"   ✓ {payload['agent']} {payload['elapsed']:.1f}s | tokens: "
                                 f"in={payload['input_tokens']}, out={payload['output_tokens']} | "
                                 f"`{payload['model']}`{retry}")

                result = asyncio.run(run_scenario(scenario_data, location=loc, on_event=on_event))
                total_t = result.timings["total"]
                st.write(f"\n🎉 **Total elapsed: {total_t:.1f}s**")
                st.session_state.last_result = result

                # Save to history
                key = f"{scenario_id}__{loc.slug}"
                st.session_state.results_history[key] = result

                status.update(label=f"✓ Selesai {total_t:.1f}s "
                                    f"({result.footprint.total_tokens:,} tokens) — "
                                    f"saved to history.",
                              state="complete")
            except Exception as e:
                status.update(label=f"✗ Gagal: {e}", state="error")
                st.exception(e)
                st.stop()

    # ─── Display last_result (persists across reruns) ───
    result = st.session_state.last_result
    if result is not None:
        st.divider()

        # ─── Dashboard cards at top ───
        st.subheader("📊 Dashboard Quick Glance")
        _dashboard_cards(result)
        with st.expander("🔗 Nexus coupling — pemeriksaan deterministik", expanded=True):
            _checks_panel(result.nexus)
        st.divider()

        # Location banner
        loc = st.session_state.resolved_location
        if loc is not None:
            st.info(
                f"📍 **{loc.display}** | lat={loc.lat:.3f}, lon={loc.lon:.3f}"
                + (f" | pop={loc.population:,}" if loc.population else "")
            )

        # ─── PDF Download ───
        col_dl, col_info = st.columns([1, 3])
        with col_dl:
            try:
                pdf_bytes = generate_scenario_report(result, include_tool_outputs=False)
                st.download_button(
                    "📄 Download PDF Report",
                    data=pdf_bytes,
                    file_name=(f"wef_agentic_{loc.slug}_"
                                f"{result.scenario.get('name', 'report').replace(' ', '_')}.pdf"),
                    mime="application/pdf",
                    width="stretch",
                )
            except Exception as e:
                st.error(f"PDF gen failed: {e}")
        with col_info:
            st.caption("📑 PDF berisi: cover, coordinator synthesis, critic audit, "
                        "per-agent outputs + charts, nexus footprint, references.")

        # ─── Build all charts ───
        charts = {
            "water": water_chart(result.water),
            "energy": energy_chart(result.energy),
            "food": food_chart(result.food),
            "critic": critic_chart(result.critic),
            "coordinator": coordinator_chart(result),
        }

        st.divider()
        st.subheader("🧭 Coordinator Synthesis")
        st.markdown(result.coordinator.content)
        if charts["coordinator"] is not None:
            st.plotly_chart(charts["coordinator"], width="stretch")

        st.subheader("🔍 Critic Audit")
        col_text, col_chart = st.columns([2, 1])
        with col_text:
            st.markdown(result.critic.content)
        with col_chart:
            if charts["critic"] is not None:
                st.plotly_chart(charts["critic"], width="stretch")

        st.subheader("Detail per Agent")
        _agent_card("Water Agent", result.water, icon="💧", chart_fig=charts["water"])
        _agent_card("Energy Agent", result.energy, icon="⚡", chart_fig=charts["energy"])
        _agent_card("Food Agent", result.food, icon="🌾", chart_fig=charts["food"])

        st.divider()
        st.subheader("🌐 Nexus Footprint (WEF 2026b)")
        st.caption("Estimasi proxy (bukan measurement). Metode air: Li et al. (2023); "
                   "semua faktor di config/llm.yaml → footprint.")
        _footprint_panel(result.footprint)

    else:
        st.info(
            "👈 (1) Pilih lokasi → (2) pilih skenario (5 opsi: BAU, JETP, Net-Zero, "
            "Climate Stress, Tourism Boom) → (3) klik **Run Scenario**."
        )


# ═══════════════════════════════════════════════════════════════════════════
# TAB: Compare
# ═══════════════════════════════════════════════════════════════════════════

with tab_compare:
    st.subheader("Comparison Mode")
    st.caption(
        f"Hasil scenario yang sudah dijalankan akan otomatis tersimpan di history "
        f"(saat ini: {len(st.session_state.results_history)} hasil). "
        f"Pilih 2-3 untuk dibandingkan."
    )
    _comparison_panel()


# ═══════════════════════════════════════════════════════════════════════════
# TAB: Data Sources
# ═══════════════════════════════════════════════════════════════════════════

with tab_data:
    if st.session_state.resolved_location is not None:
        _provenance_panel(st.session_state.resolved_location)
    else:
        st.info("Pilih lokasi di sidebar dulu.")

    st.divider()
    st.subheader("📥 Manual Override (JSON Upload)")
    st.caption(
        "Upload file JSON dengan format di bawah untuk override data tertentu "
        "dari sumber otoritatif lokal (mis. data resmi BMKG/BPS yang Anda download manual)."
    )

    with st.expander("📐 JSON Schema + Example", expanded=False):
        st.markdown("**Schema:**")
        st.json(manual_override_schema())
        st.markdown("**Example file `override_sleman_-7.730_110.360.json`:**")
        example = {
            "version": "1.0",
            "location": {
                "name": "Sleman", "lat": -7.73, "lon": 110.36, "country_code": "ID",
            },
            "variables": {
                "climate.precip_mm_annual": {
                    "value": 2200,
                    "year": 2023,
                    "source": "BMKG Stasiun Borobudur 2023",
                    "note": "Data resmi BMKG, downloaded manual dari dataonline.bmkg.go.id",
                },
                "socio.population": {
                    "value": 1142528,
                    "year": 2024,
                    "source": "BPS Sleman 2024 Proyeksi",
                },
                "food.rice_area_ha": {
                    "value": 38500,
                    "year": 2024,
                    "source": "Distan Sleman Laporan Triwulan IV 2024",
                },
            },
        }
        st.json(example)

    uploaded = st.file_uploader("Upload JSON override", type=["json"])
    if uploaded is not None:
        import json
        try:
            payload = json.load(uploaded)
            # Save to data/external/override_<slug>.json
            from wef_agentic.config.settings import EXTERNAL_DIR
            loc = st.session_state.resolved_location
            EXTERNAL_DIR.mkdir(parents=True, exist_ok=True)
            out_path = EXTERNAL_DIR / f"override_{loc.slug}.json"
            with open(out_path, "w") as f:
                json.dump(payload, f, indent=2)
            n_vars = len(payload.get("variables", {}))
            st.success(f"✓ Override tersimpan di `{out_path.name}`. "
                       f"{n_vars} variables akan dipakai saat agen dipanggil.")
            st.json(payload)
        except Exception as e:
            st.error(f"Parse error: {e}")
