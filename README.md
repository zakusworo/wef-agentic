# WEF-Agentic

**Multi-city agentic AI framework untuk Water-Energy-Food Nexus governance** — operasionalisasi WEF 2026 readiness functions di tingkat sub-nasional, dengan tracking nexus footprint dari LLM usage-nya sendiri.

Operasionalisasi dua framework WEF 2026:

- **WEF (2026a)** *Making Agentic AI Work for Government: A Readiness Framework* (April 2026)
- **WEF (2026b)** *Building Resilient and Scalable AI Value Chains: A Nexus Strategy* (May 2026)

Spec lengkap: [`../WEF-Agentic.md`](../WEF-Agentic.md)

> **Status:** Phase 1 complete — 5 agen × 5 skenario × multi-city × data sources framework × comparison mode × PDF export.

---

## ✨ Features Highlight

| Domain | Capability |
|---|---|
| **Agents** | 5 LLM-backed agen (Coordinator, Water, Energy, Food, Critic) dengan tool-use loop |
| **Scenarios** | 5 skenario pre-defined (BAU, JETP-Aligned, Net-Zero 2045, Climate Stress SSP5-8.5, Tourism Boom) |
| **Multi-city** | Preset Sleman (BPS lengkap) + custom city via Open-Meteo geocoding (Bandung, Marrakesh, dll.) |
| **Data sources** | 5 providers ber-tier (Manual / BPS / Open-Meteo / World Bank / Country-proxy) dengan DataResolver fallback |
| **Provenance** | Setiap variable membawa source, year, unit, confidence (0-1), tier, note |
| **LLM providers** | 3 backend swap-able (Ollama Local / Ollama Cloud / Claude Agent SDK) — runtime override via env |
| **Nexus footprint** | Tokens → kWh → liter air → CO₂eq tracked per run |
| **Reporting** | PDF report dengan 5 matplotlib charts embedded + provenance + bounded-autonomy notice |
| **UI** | Streamlit 3-tab (Run / Compare / Data Sources) dengan live progress, dashboard cards, radar trade-off chart |

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   geo/ (Location, Open-Meteo geocoding)         │
└──────────────────────┬──────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────────┐
│  data/sources/ (5 providers, tier 1-3)                          │
│    Manual → BPS → Open-Meteo → World Bank → Country-Proxy       │
│              ↓ DataResolver (priority cascade)                  │
│              DataPacket(value, source, year, confidence, tier)  │
└──────────────────────┬──────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────────┐
│  physics/ (water_balance · energy_demand · crop_yield)          │
│  tools/   (10 registered, JSON-callable)                        │
└──────────────────────┬──────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────────┐
│  agents/  (5 agen + base)        ─┐                             │
│  llm/     (Ollama L/C, Claude)    ├─▶  orchestration/  (graph)  │
│  llm/footprint.py                 │                             │
└────────────────────────────────────┴──────────────────────────┐ │
                                                                ▼ ▼
┌─────────────────────────────────────────────────────────────────┐
│  reporting/ (matplotlib + reportlab PDF)                        │
│  ui/streamlit_app.py (Run · Compare · Data Sources tabs)        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### 1. Install

```bash
cd "/mnt/e/WEF Project/wef-agentic"
python3 -m venv .venv
source .venv/bin/activate           # WSL / Linux / macOS
# .venv\Scripts\activate            # Windows
pip install -e ".[dev]"
```

### 2. Pilih LLM Provider

Copy `.env.example` → `.env`, isi key yang relevan:

```bash
# Opsi A — Claude Agent SDK (pakai Claude Code subscription, tidak perlu API key)
WEF_AGENTIC_PROVIDER_OVERRIDE=claude-agent-sdk

# Opsi B — Ollama Cloud ($20/bulan, 3 concurrent — RECOMMENDED untuk production runs)
OLLAMA_API_KEY=ollama-...
WEF_AGENTIC_PROVIDER_OVERRIDE=ollama-cloud

# Opsi C — Ollama Local (gratis, butuh `ollama serve`)
WEF_AGENTIC_PROVIDER_OVERRIDE=ollama-local
OLLAMA_HOST=http://localhost:11434
```

Per-agent default ada di `src/wef_agentic/config/llm.yaml`. Env var override dipakai jika di-set; kosong = pakai yaml.

### 3. Bootstrap Data (opsional)

```bash
# Fetch real climate data Open-Meteo + cache parquet (butuh internet)
python -m wef_agentic.data.bootstrap

# Atau pakai fixture synthetic kalibrasi BPS-BMKG (offline, instant)
python tests/generate_fixture.py
```

### 4. Run UI

```bash
streamlit run src/wef_agentic/ui/streamlit_app.py
# → http://localhost:8501
```

---

## 🧠 Core Concepts

### 5 Agen

| Agent | Role | Default model (yaml) |
|---|---|---|
| **Coordinator** | Decompose query, sintesis hasil, sorot trade-off WEF | `deepseek-v4-pro:cloud` (max_tokens 3000) |
| **Water** | Thornthwaite-Mather water balance, irrigation demand | `deepseek-v4-pro:cloud` |
| **Energy** | Elasticity-based demand projection, grid emissions | `deepseek-v4-pro:cloud` |
| **Food** | Doorenbos-Kassam yield, SSL (Self-Sufficiency Level) | `deepseek-v4-pro:cloud` |
| **Critic** | Audit konsistensi, mass-balance, bias, error consequence (WEF 2026a) | `kimi-k2.6:cloud` |

Setiap agen punya 3 field model di yaml (`model_local` / `model` / `model_claude`) — provider swap tidak mengubah agen, hanya backend.

### 5 Skenario

| ID | Nama | Climate Δ | Policy Pivot |
|---|---|---|---|
| `S1_BAU_2030` | BAU 2030 | P −2%, T +0.7°C | No intervention |
| `S2_JETP_Aligned` | JETP-Aligned 2030 | P −3%, T +1.0°C | EBT 34%, LP2B moderate, induction partial |
| `S3_NetZero_2045` | Net-Zero 2045 | P −1%, T +0.5°C | EBT 45%, LP2B strict, EV+induction full |
| `S4_Climate_Stress` | Climate Stress 2030 | P −15%, T +1.8°C | SSP5-8.5 + drought + Merapi VEI 3 di T+3 |
| `S5_Tourism_Boom` | KSPN Borobudur Boom 2030 | P −3%, T +1.0°C | 2 juta+ wisatawan, LP2B lax, hospitality conversion |

Skenario location-agnostic — `get_scenario("S2_JETP_Aligned", location_query="Bandung")` override target city.

### Data Sources Framework

5 providers terdaftar di `data/sources/`, dipilih DataResolver berdasarkan **tier priority**:

| Tier | Provider | Cakupan | Confidence |
|---|---|---|---|
| 🟢 1 | `ManualOverrideSource` | Upload JSON user via UI | 0.99 |
| 🟢 1 | `BPSStaticSource` | Sleman only (4 variable, BPS Statistik 2023) | 0.95 |
| 🟢 1 | `OpenMeteoSource` | Global, 3 climate variable, ERA5 reanalysis (10-yr mean) | 0.92 |
| 🟡 2 | `WorldBankSource` | Country-level, 3 indicator via REST API | 0.75 |
| 🔴 3 | `CountryProxySource` | Last-resort static defaults per ISO code | 0.55 |

**11 standardized variables** di domain `climate.*`, `socio.*`, `energy.*`, `food.*`, `grid.*`. Setiap fetch menghasilkan `DataPacket` dengan provenance lengkap (source, year, unit, confidence, tier, note).

Manual override format ada di `data/external/override_<slug>.json`, schema dari `registry.manual_override_schema()`.

### Multi-City

- **Preset**: hardcoded `Location` dengan country/region/coords lengkap (saat ini hanya Sleman, BPS data tier 1).
- **Custom**: nama kota apa saja → Open-Meteo geocoding (gratis, no key) → resolve country code → fetch climate realtime → fallback country-proxy untuk variable yang tidak tersedia.

Verified: Sleman cached fixture water balance 0.33s · Bandung fresh fetch 1.95s · Marrakesh full chain 11.3s (Morocco, deficit 1481mm, semi-arid).

### Nexus Footprint

Setiap run melacak LLM footprint-nya sendiri (operasionalisasi WEF 2026b):

```
Energy (kWh)   ≈ tokens × 0.0003 / 1000        (proxy public estimate)
Water (L)      ≈ tokens × 0.005 / 1000         (Zhang et al. 2025 proxy)
CO₂eq (kg)     ≈ kWh × 0.4                      (US grid mix average)
```

> **Honest caveat:** angka adalah *order-of-magnitude*, bukan measurement. Konstanta proxy dikonfigurasi di `config/llm.yaml` → `footprint:`.

### PDF Reporting

`reporting/pdf.py` → file `wef_agentic_<location-slug>_<scenario>.pdf`:

- Cover + metadata + bounded-autonomy notice
- Coordinator synthesis + Critic audit (charts embedded)
- 3 per-agent sections dengan matplotlib charts
- Nexus footprint table + references

Charts (matplotlib untuk PDF, plotly untuk UI):

- 💧 Water: monthly balance + soil moisture
- ⚡ Energy: demand projection 2023-2050 dengan annotated endpoints
- 🌾 Food: area+yield dual-axis + production bars
- 🔍 Critic: donut distribusi findings (KONSISTEN / INKONSISTEN / MISSING / ERROR-HIGH)
- 🧭 Coordinator: token usage per agent

---

## 🖥 UI Walkthrough (3 tabs)

**▶ Run Scenario**

- Sidebar: provider switcher, model override, location selector (preset Sleman atau custom city)
- Pilih 1 dari 5 skenario → live progress logs via `st.status` (per-agen timing, tokens, tool calls)
- Dashboard cards 5 metrics: water deficit, demand 2030, SSL padi, CO₂eq, total tokens
- Download PDF report

**📊 Compare Scenarios**

- Multi-select 2-3 hasil dari history
- Comparison table cross-scenario
- Radar chart trade-off (water security · energy efficiency · food security · low-CO₂ · token efficiency, semua dinormalisasi 0-1)
- Coordinator synthesis side-by-side

**🔬 Data Sources**

- Provenance panel: per-variable source + tier + confidence + note
- JSON upload untuk manual override (validated terhadap `manual_override_schema`)

---

## 📁 Project Structure

```
wef-agentic/
├── README.md
├── pyproject.toml                  # deps + ruff config (RUF001/002 ignored)
├── .env.example                    # env vars (WEF_AGENTIC_*, OLLAMA_*)
├── .gitignore
├── data/
│   ├── raw/                        # untouched downloads
│   ├── processed/                  # parquet cache (gitignored)
│   └── external/                   # manual JSON overrides
├── src/wef_agentic/
│   ├── config/                     # settings.py, llm.yaml
│   ├── geo/                        # Location, Open-Meteo geocoding, presets
│   ├── data/
│   │   ├── bps_static.py           # Sleman hardcoded BPS
│   │   ├── country_defaults.py     # 20+ negara ISO defaults
│   │   ├── openmeteo.py            # historical climate fetch
│   │   ├── nasa_power.py           # alternative climate fetch
│   │   ├── bootstrap.py            # cache priming CLI
│   │   └── sources/                # ← Data Sources Framework
│   │       ├── base.py             # DataPacket, DataSource ABC
│   │       ├── registry.py         # 11 VariableSpec
│   │       ├── resolver.py         # DataResolver priority cascade
│   │       ├── manual_source.py
│   │       ├── bps_static_source.py
│   │       ├── openmeteo_source.py
│   │       ├── worldbank_source.py
│   │       └── proxy_source.py
│   ├── physics/                    # water_balance, energy_demand, crop_yield
│   ├── tools/                      # registry + water/energy/food (10 tools)
│   ├── llm/
│   │   ├── provider.py             # factory + env override
│   │   ├── ollama_provider.py      # local + cloud
│   │   ├── claude_agent_provider.py
│   │   ├── footprint.py            # nexus tracking
│   │   └── types.py
│   ├── agents/                     # base + coordinator + critic + water/energy/food
│   ├── orchestration/              # graph (water||energy||food → critic → coordinator), scenarios
│   ├── reporting/                  # charts (plotly), pdf_charts (matplotlib), pdf (reportlab)
│   ├── readiness/                  # WEF 2026a function mapping
│   ├── analysis/                   # cross-scenario helpers
│   └── ui/                         # streamlit_app.py
└── tests/
    ├── smoke_no_llm.py             # imports + tools + physics (~1s)
    ├── smoke_llm.py                # 1 agen via Ollama (~15s)
    ├── smoke_e2e_sleman.py         # full 5-agen pipeline Sleman (~10min llama3.2:1b · ~60s cloud)
    ├── smoke_e2e.py                # legacy multi-city variant
    ├── generate_fixture.py         # regenerate calibrated fixture
    ├── fixtures/
    ├── unit/
    └── integration/
```

---

## 🧪 Testing

```bash
# 1-second sanity — imports, tools, physics, scenarios (no LLM)
python tests/smoke_no_llm.py

# Single agent via Ollama local
python tests/smoke_llm.py

# Full 5-agen pipeline Sleman fixture
python tests/smoke_e2e_sleman.py

# Lint (RUF001/002 ignored untuk emoji/Indonesia)
ruff check src/wef_agentic

# Compile-check
python -m compileall -q src/wef_agentic
```

### Verified end-to-end timings (Sleman, S2 JETP-Aligned, 2026-05-17)

Pipeline penuh 5 agen pakai cached fixture Sleman, tergantung model backend:

| Backend | Phase 1 (parallel) | Phase 2 (critic) | Phase 3 (coord.) | Total | Tokens |
|---|---:|---:|---:|---:|---:|
| `llama3.2:1b` (local, smoke-only) | 18.9s | 414.9s | 145.5s | **579.3s** (~10 min) | 11,662 |
| `gemma4:e4b` (local, production-grade) | *TBD* | *TBD* | *TBD* | *est. 60–120s* | — |
| `deepseek-v4-pro:cloud` / `kimi-k2.6:cloud` (Ollama Cloud, 3-concurrent) | *TBD* | *TBD* | *TBD* | *est. 30–60s* | — |

> **Catatan:** `llama3.2:1b` adalah model smoke-only (verify pipeline jalan), bukan untuk output produksi. Untuk run produktif gunakan `gemma4:e4b` local atau Ollama Cloud (3 concurrent paralelisasi domain agents). Critic + Coordinator dominan saat token output panjang — bottleneck di model kecil.

### Sleman fixture re-calibrated (2026-05-16)

- Precip 2617 mm/yr, ET₀ 1483 mm/yr — match BPS-BMKG (~2200 mm, ~1300-1500 mm)
- File: `data/processed/openmeteo_sleman_1991-01-01_2024-12-31.parquet`

---

## 🎯 Functions WEF 2026a yang Ditarget

- 🟢 **#15** Policy implementation monitoring — *high readiness* (LP2B alih fungsi)
- 🔴 **#43** Policy forecasting & scenario modelling — *low readiness* (**INTI**)
- 🔴 **#55** Policy impact prediction — *low readiness* (**INTI**)

> **Bounded autonomy:** Semua output framework ditandai `[ADVISORY-ONLY]` untuk functions di low-readiness area. Human-on-the-loop wajib sebelum decision-making.

---

## 🗺 Roadmap

- **Phase 0 (DONE)** — MVP framework: 5 agen, 3 skenario, dual-provider
- **Phase 1 (DONE, 2026-05-16)** — Data sources framework, multi-city, comparison mode, PDF report, 5 skenario, dashboard cards, calibrated fixture
- **Phase 2 (pending)** — Policy Agent + 4 Stakeholder Agents (Farmer / Pemda / PLN / Community), SWAT+/OSeMOSYS/AquaCrop coupling, CMIP6 ensemble, Sobol sensitivity, MCDA, paper v0.1
- **Phase 3 (pending)** — Stakeholder workshop, real-time BMKG/BPS API integration (butuh registration key), paper v1.0

Detail di [`../WEF-Agentic.md`](../WEF-Agentic.md) §8.

---

## 📜 License

MIT — code · CC-BY 4.0 — paper & data.

---

## 📚 Citation

```bibtex
@misc{kusworo2026wefagentic,
  author    = {Kusworo, Zulfikar Aji},
  title     = {WEF-Agentic: Multi-city agentic AI framework for sub-national
               Water-Energy-Food Nexus governance},
  year      = {2026},
  publisher = {GitHub},
  note      = {Operasionalisasi WEF (2026a, 2026b).
               Politeknik Energi dan Pertambangan Bandung.}
}
```
