# WEF-Agentic

**Multi-city agentic AI framework untuk Water-Energy-Food Nexus governance** — operasionalisasi WEF 2026 readiness functions di tingkat sub-nasional, dengan tracking nexus footprint dari LLM usage-nya sendiri.

Operasionalisasi dua framework WEF 2026:

- **WEF (2026a)** *Making Agentic AI Work for Government: A Readiness Framework* (April 2026)
- **WEF (2026b)** *Building Resilient and Scalable AI Value Chains: A Nexus Strategy* (May 2026)

Spec lengkap: `WEF-Agentic.md` (dokumen desain internal, tidak termasuk di repo ini).

> **Status:** Phase 1 complete — deterministic nexus coupling × 5 agen × 5 skenario × multi-city × data sources framework × comparison mode × PDF export × offline test suite + CI.

---

## ✨ Features Highlight

| Domain | Capability |
|---|---|
| **Nexus coupling** | Deterministik, sebelum LLM: water balance → water stress → yield; pompa irigasi → demand listrik; demand listrik → konsumsi air pembangkit. Plus pemeriksaan konsistensi otomatis |
| **Agents** | 5 LLM agen (Water, Energy, Food, Critic, Coordinator) yang *menginterpretasi* hasil model — scripted tool pipeline, bukan LLM tool-calling |
| **Scenarios** | 5 skenario pre-defined (BAU, JETP-Aligned, Net-Zero 2045, Climate Stress SSP5-8.5, Tourism Boom) |
| **Multi-city** | Preset Sleman (BPS lengkap) + custom city via Open-Meteo geocoding (Bandung, Marrakesh, dll.) |
| **Data sources** | 6 providers ber-tier (Manual / BPS / Open-Meteo / Gazetteer / World Bank / Country-proxy) via DataResolver — dipakai langsung oleh tools |
| **Provenance** | Setiap input membawa source, year, unit, confidence (0-1), tier, note; input low-confidence di-flag |
| **LLM providers** | 3 backend swap-able (Ollama Local / Ollama Cloud / Claude Agent SDK) — runtime override via env |
| **Robustness** | Jawaban kosong (reasoning model kehabisan token) → retry dengan budget 2× → gagal eksplisit, tidak diteruskan diam-diam |
| **Nexus footprint** | Tokens → kWh (per ukuran model, PUE) → air on-site + off-site → CO₂eq (grid per provider) |
| **Reproducibility** | Run record JSON: git SHA, config, prompt hash, model yang dilaporkan backend, done_reason, output lengkap |
| **Reporting** | PDF report: charts, tabel pemeriksaan deterministik, provenance, bounded-autonomy notice |
| **UI** | Streamlit 3-tab (Run / Compare / Data Sources) dengan live progress, dashboard cards, radar trade-off chart |

---

## 🏗 Architecture

```
 scenario + Location
        │
        ▼
┌──────────────────────────────────────────────────────────────────┐
│ orchestration/nexus.py — compute_nexus()  (deterministik, no LLM) │
│                                                                  │
│  data/sources DataResolver ──► tools/ (water · energy · food)    │
│                                  │                               │
│  climate Δ ─► Thornthwaite-Mather (skenario & baseline iklim)    │
│                 ├─► water stress setelah irigasi ─► Doorenbos-    │
│                 │     Kassam yield ─► produksi ─► SSL             │
│                 └─► pompa air tanah (Δ iklim) ─► +GWh demand      │
│  demand × porsi EBT ─► emisi CO₂ + konsumsi air pembangkit       │
│                                                                  │
│  run_checks(): mass balance · seasonal mismatch · groundwater vs │
│  recharge proxy · populasi konsisten · yield plausibility ·      │
│  low-confidence inputs                                           │
└───────────────────────────────┬──────────────────────────────────┘
                                │ NexusState (angka kunci + checks)
            ┌───────────────────┼───────────────────┐
            ▼                   ▼                   ▼
       Water Agent        Energy Agent         Food Agent      (paralel)
            └───────────────────┼───────────────────┘
                                ▼
            Critic Agent — audit narasi vs angka kunci + checks
                                ▼
            Coordinator — sintesis trade-off + rekomendasi
                                ▼
       footprint · run record · PDF (reporting/) · Streamlit (ui/)
```

---

## 🚀 Quick Start

### 1. Install

```bash
cd wef-agentic
python3.11 -m venv .venv
source .venv/bin/activate           # Linux / macOS / WSL
# .venv\Scripts\activate            # Windows
pip install -e ".[dev]"             # + ".[dev,claude]" untuk Claude Agent SDK
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
python scripts/generate_fixture.py
```

### 4. Run

```bash
streamlit run src/wef_agentic/ui/streamlit_app.py      # UI → http://localhost:8501

python scripts/run_scenario.py S2_JETP_Aligned          # CLI, simpan run record ke docs/runs/
python scripts/run_scenario.py S1_BAU_2030 --location Bandung --provider ollama-local --model gemma4:e4b
```

---

## 🧠 Core Concepts

### Siapa menghitung apa

Semua angka dihitung **deterministik** oleh `compute_nexus()` sebelum LLM dipanggil. Agen menerima angka tersebut dan diinstruksikan untuk mengutip, bukan menghitung ulang. Critic mengaudit narasi agen terhadap *angka kunci* dan hasil *pemeriksaan deterministik*. Dengan begitu kesalahan numerik LLM bisa dideteksi, dan hasil model fisik tidak bergantung pada model bahasa yang dipakai.

Tool registry (`tools/`) tetap menyediakan JSON schema per tool; saat ini tools dipanggil oleh pipeline, bukan dipilih oleh LLM.

### 5 Agen

| Agent | Role | Default model (yaml) |
|---|---|---|
| **Water** | Interpretasi water balance (surplus/defisit tahunan & musiman), stress, irigasi, air tanah | `deepseek-v4-pro:cloud` |
| **Energy** | Interpretasi proyeksi demand, tambahan pompa irigasi, emisi, air pembangkit | `deepseek-v4-pro:cloud` |
| **Food** | Interpretasi yield, produksi, SSL — atau kesenjangan data jika luas panen lokal tidak ada | `deepseek-v4-pro:cloud` |
| **Critic** | Fidelity angka, konsistensi antar-sektor, tanggapan atas WARN/FAIL, bias, error consequence (WEF 2026a) | `kimi-k2.6:cloud` (max_tokens 8000) |
| **Coordinator** | Sintesis trade-off, uncertainty, rekomendasi untuk pemerintah daerah lokasi | `deepseek-v4-pro:cloud` (max_tokens 6000) |

Setiap agen punya 3 field model di yaml (`model_local` / `model` / `model_claude`) — provider swap tidak mengubah agen, hanya backend.

**Jawaban kosong tidak pernah diteruskan.** Reasoning model (mis. Kimi K2.6) bisa menghabiskan seluruh budget untuk `thinking`. Base agent me-retry sekali dengan budget 2× (cap `retry.max_tokens_cap` di `llm.yaml`); jika tetap kosong, run gagal dengan `EmptyCompletionError`. Token dari semua attempt dihitung di footprint.

### 5 Skenario

| ID | Nama | Climate Δ | Policy Pivot |
|---|---|---|---|
| `S1_BAU_2030` | BAU 2030 | P −2%, T +0.7°C | No intervention |
| `S2_JETP_Aligned` | JETP-Aligned 2030 | P −3%, T +1.0°C | EBT 34%, LP2B moderate, induction partial |
| `S3_NetZero_2045` | Net-Zero 2045 | P −1%, T +0.5°C | EBT 45%, LP2B strict, EV+induction full |
| `S4_Climate_Stress` | Climate Stress 2030 | P −15%, T +1.8°C | SSP5-8.5 + drought + Merapi VEI 3 di T+3 |
| `S5_Tourism_Boom` | KSPN Borobudur Boom 2030 | P −3%, T +1.0°C | 2 juta+ wisatawan, LP2B lax, hospitality conversion |

Skenario location-agnostic — `get_scenario("S2_JETP_Aligned", location_query="Bandung")` override target city. Water stress **bukan** input skenario: diturunkan dari climate Δ. Untuk sensitivity run, set `water_stress_override` (run akan membawa peringatan).

### Nexus Coupling

Parameter di `src/wef_agentic/config/nexus.yaml`; nilai bertanda `ASSUMPTION` adalah default screening yang harus dikalibrasi dengan data lokal.

| Link | Perhitungan |
|---|---|
| Iklim → air | Thornthwaite-Mather bulanan dengan retensi eksponensial `S = C·exp(−APWL/C)`, storage awal = steady state (spin-up) |
| Air → pangan | `stress = (1 − ETa/PET) × (1 − supply_fraction)` → Doorenbos-Kassam `Ya/Ymax = 1 − Ky·stress` |
| Air → energi | air tanah = defisit / efisiensi × supply × porsi air tanah × luas fisik; `E = ρgH/η`; yang ditambahkan ke demand adalah selisih skenario − iklim baseline, di-ramp ke tahun horizon |
| Energi → air | konsumsi air pembangkit = demand × (porsi fosil × 2.6 + porsi EBT × 0.1) m³/MWh — off-site, dilaporkan, tidak dikurangkan dari neraca lokal |
| Populasi | sektor energi & pangan memakai populasi dasar dan laju pertumbuhan yang sama (dicek) |

Pemeriksaan deterministik (`ok` / `warn` / `fail`) masuk ke prompt Critic & Coordinator, UI, PDF, dan run record.

### Data Sources Framework

6 providers terdaftar di `data/sources/`, dipilih DataResolver berdasarkan **tier priority**:

| Tier | Provider | Cakupan | Confidence |
|---|---|---|---|
| 🟢 1 | `ManualOverrideSource` | Upload JSON user via UI | 0.99 |
| 🟢 1 | `BPSStaticSource` | Sleman only (populasi, listrik, luas panen, alih fungsi lahan, yield) | 0.95 |
| 🟢 1 | `OpenMeteoSource` | Global, 3 climate variable, ERA5 reanalysis (10-yr mean) | 0.92 |
| 🟡 2 | `GeocodedPopulationSource` | Populasi GeoNames dari hasil geocoding (kota, bukan negara) | 0.70 |
| 🟡 2 | `WorldBankSource` | Country-level per-kapita indicators (GDP, listrik) via REST API | 0.75 |
| 🔴 3 | `CountryProxySource` | Last-resort static defaults per ISO code | 0.55 |

World Bank tidak lagi melayani `socio.population` (itu total negara, bukan kota). Jika populasi tidak diketahui sama sekali, fallback 100k dipakai **dengan** provenance confidence 0.1 dan peringatan.

**12 standardized variables** di domain `climate.*`, `socio.*`, `energy.*`, `food.*`, `grid.*`. Manual override format ada di `data/external/override_<slug>.json`, schema dari `registry.manual_override_schema()`.

### Multi-City

- **Preset**: hardcoded `Location` dengan data lokal (saat ini hanya Sleman, BPS tier 1).
- **Custom**: nama kota apa saja → Open-Meteo geocoding (gratis, no key) → fetch climate realtime → per-kapita country proxy. Match yang dipilih user di UI dipin, jadi geocoding ulang tidak bisa memilih kota lain dengan nama sama.
- **Proyeksi pangan butuh luas panen lokal.** Tanpa BPS/manual override, proyeksi pangan dan coupling pompa irigasi dilaporkan *unavailable* — tidak meminjam lahan Sleman.

### Nexus Footprint

Setiap run melacak LLM footprint-nya sendiri (operasionalisasi WEF 2026b), konstanta di `config/llm.yaml → footprint:`:

```
IT energy (kWh)   = (output + 0.1·input tokens)/1000 × 0.0003 × size multiplier (small 0.1 · medium 1 · large 3)
Facility energy   = IT energy × PUE                     (per provider)
Water on-site (L) = IT energy × WUE                     (Li et al. 2023: 0.55 L/kWh, US)
Water off-site(L) = facility energy × EWIF              (Li et al. 2023: 3.14 L/kWh, US)
CO₂eq (kg)        = facility energy × grid factor       (local: Jawa-Bali 0.85; cloud: US 0.4)
```

> **Honest caveat:** angka adalah *order-of-magnitude*, bukan measurement. Faktor yang tidak diketahui (mis. EWIF grid Indonesia untuk run lokal) dilaporkan sebagai *missing*, bukan nol.

### PDF Reporting

`reporting/pdf.py` → file `wef_agentic_<location-slug>_<scenario>.pdf`:

1. Coordinator synthesis · 2. Critic audit · 3. Nexus coupling & pemeriksaan deterministik · 4–6. Water / Energy / Food · 7. Nexus footprint · 8. References

Charts (matplotlib untuk PDF, plotly untuk UI): water balance bulanan + soil moisture, proyeksi demand (2030 / horizon / 2050), luas+yield+produksi, donut temuan Critic, token per agen.

---

## 🖥 UI Walkthrough (3 tabs)

**▶ Run Scenario**

- Sidebar: provider switcher, model override, location selector (preset Sleman atau custom city)
- Pilih 1 dari 5 skenario → live progress 4 fase (nexus → domain paralel → critic → coordinator), per-agen timing, tokens, model yang dilaporkan, retry
- Dashboard cards: water deficit + stress, demand 2030 + tambahan pompa, SSL padi, CO₂eq, tokens
- Panel pemeriksaan deterministik + peringatan
- Download PDF report

**📊 Compare Scenarios** — tabel lintas skenario, radar trade-off (dinormalisasi 0-1), sintesis side-by-side

**🔬 Data Sources** — provenance per-variable + JSON upload manual override

---

## 📁 Project Structure

```
wef-agentic/
├── pyproject.toml                  # deps (+ extras: dev, claude) + ruff + pytest config
├── .github/workflows/ci.yml        # ruff + pytest on Python 3.11
├── data/{raw,processed,external}/  # downloads · parquet cache (gitignored) · manual overrides
├── docs/runs/                      # run records
├── scripts/
│   ├── run_scenario.py             # CLI end-to-end run → docs/runs/*.json
│   ├── generate_fixture.py         # synthetic Sleman climate fixture
│   └── smoke_llm.py                # manual check against a real local Ollama
├── src/wef_agentic/
│   ├── config/                     # settings.py, llm.yaml, nexus.yaml
│   ├── geo/                        # Location, geocoding, presets, resolve cache
│   ├── data/                       # BPS static, country defaults, Open-Meteo, fixture, sources/
│   ├── physics/                    # water_balance, crop_yield, energy_demand, coupling
│   ├── tools/                      # registry + water/energy/food tools
│   ├── llm/                        # providers, types, footprint
│   ├── agents/                     # base + water/energy/food/critic/coordinator
│   ├── orchestration/              # nexus (deterministic), graph (pipeline), runlog, scenarios
│   ├── reporting/                  # charts (plotly), pdf_charts (matplotlib), pdf (reportlab)
│   └── ui/                         # streamlit_app.py
└── tests/
    ├── conftest.py                 # offline fixture data, network blocked, FakeProvider
    ├── unit/                       # physics, coupling, footprint, providers, retry, tools
    └── integration/                # full pipeline (Sleman + custom city), PDF, run record
```

---

## 🧪 Testing

```bash
pytest                               # offline: synthetic fixture, no network, fake LLM (~15s)
ruff check src tests scripts

python scripts/smoke_llm.py gemma4:e4b    # optional: real local Ollama
```

CI (`.github/workflows/ci.yml`) menjalankan ruff + pytest di setiap push/PR.

### Historical run (pre-coupling, 2026-05-17)

[`docs/runs/run_S2_JETP_Aligned_deepseek_cloud_20260517_110212.json`](docs/runs/run_S2_JETP_Aligned_deepseek_cloud_20260517_110212.json) — Ollama Cloud, `deepseek-v4-pro` (domain + coordinator) / `kimi-k2.6` (critic): 31.1s domain paralel · 130.3s critic · 47.9s coordinator · 19,813 tokens.

Run ini dibuat **sebelum** perubahan berikut dan tidak lagi mewakili output framework:

- Critic menghabiskan 3,000 token untuk reasoning sehingga output kosong, dan Coordinator tetap mensintesis tanpa audit. Sekarang: critic `max_tokens` 8000, retry, dan run gagal eksplisit jika tetap kosong.
- Water stress saat itu konstanta skenario (7%), belum diturunkan dari water balance.
- Footprint memakai konstanta per-token tunggal.

Jalankan ulang dengan `python scripts/run_scenario.py S2_JETP_Aligned` untuk run record format baru.

### Sleman fixture

- Synthetic, dikalibrasi terhadap BPS-BMKG (~2200-2600 mm hujan, ~1300-1550 mm ET₀); tahun 2023 stasiun Mlati → yield model 6.7 t/ha vs BPS 6.5 t/ha.
- File: `data/processed/openmeteo_sleman_1991-01-01_2024-12-31.parquet`

---

## 🎯 Functions WEF 2026a yang Ditarget

- 🟢 **#15** Policy implementation monitoring — *high readiness* (LP2B alih fungsi)
- 🔴 **#43** Policy forecasting & scenario modelling — *low readiness* (**INTI**)
- 🔴 **#55** Policy impact prediction — *low readiness* (**INTI**)

> **Bounded autonomy:** Semua output agen ditandai ADVISORY ONLY untuk functions di low-readiness area. Human-on-the-loop wajib sebelum decision-making.

---

## 🗺 Roadmap

- **Phase 0 (DONE)** — MVP framework: 5 agen, 3 skenario, dual-provider
- **Phase 1 (DONE, 2026-05-16)** — Data sources framework, multi-city, comparison mode, PDF report, 5 skenario, dashboard cards, calibrated fixture; deterministic nexus coupling + checks, test suite + CI
- **Phase 2 (pending)** — Policy Agent + 4 Stakeholder Agents (Farmer / Pemda / PLN / Community), SWAT+/OSeMOSYS/AquaCrop coupling, CMIP6 ensemble, Sobol sensitivity (termasuk parameter `nexus.yaml`), MCDA, paper v0.1
- **Phase 3 (pending)** — Stakeholder workshop, real-time BMKG/BPS API integration (butuh registration key), paper v1.0

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
