# WEF-Agentic — Progress Log

_Last updated: 2026-09-20 · local branch `finish-pending-tasks`; changes not committed or pushed_

Handoff notes for the next working session. README describes *what the framework is*; this file tracks *where the work stands* and *what to do next*.

The new [project specification](WEF-Agentic.md) defines Phase 2/3 inputs, interfaces
and acceptance criteria. It was created on 2026-09-20 at the user's request because
the former internal specification was unavailable.

## 2026-09-20 implementation and demo

- Local Python 3.14 environment installed. 59 offline tests passed outside the
  sandbox; threaded asyncio tests hang inside this sandbox. Ruff passed.
- Fixed pumping baseline land area and the multi-station water-balance fallback;
  added regression coverage and explicit growing-month / historical-year options.
- Added deterministic sweep and optional SALib Sobol scripts. A 56-evaluation
  synthetic smoke run passed; example bounds are not calibrated uncertainty ranges.
- Migrated Streamlit width arguments, raised its minimum version, checked startup
  and recorded-demo loading, and opened the demo in a browser at desktop/mobile
  widths. Tabs respond; no document-level mobile overflow was detected.
  Six chart containers rendered and the PDF download was verified in Chromium.
- Full synthetic-climate Claude S2 run succeeded in 210.66 seconds. All five
  narratives were nonempty, ended with `stop`, and needed one attempt. Reported
  models matched requested Sonnet 4.6 / Opus 4.7. This does not test forced
  output-budget exhaustion. Ollama Cloud validation still needs a key.
- The default Ollama Cloud Critic model is now `glm-5.3-flash:cloud`, replacing
  `kimi-k2.6:cloud`. Ollama documents the exact tag and describes 18B active
  parameters with always-on reasoning. A like-for-like pipeline benchmark is
  still required before claiming a latency or quality improvement.
- Real Open-Meteo 1991–2024 data for three stations and NASA POWER downloaded.
  Fixed oversized requests by fetching paced yearly chunks; added bootstrap
  `--force` because the previous command silently reused synthetic caches.
- Real-climate S2 Claude run completed in 200.26 seconds; all five agents returned
  nonempty responses on their first attempt with `stop`. No deterministic checks
  failed; seasonality and low-confidence warnings remain. Record:
  `docs/runs/run_S2_JETP_Aligned_sleman_claude-agent-sdk_20260920_144208.json`.
  Deterministic five-scenario sweeps were saved for both 2023 and 2015 climate baselines.
- Archived the obsolete May run. Rendered all three README diagrams in default
  and dark Mermaid themes; native GitHub dark-mode rendering remains unverified.
- Kept existing Claude model defaults for reproducibility after confirming they
  work live. Newer models can be evaluated with explicit overrides.
- Created [runnable demo](scripts/start_demo.sh), [specification](WEF-Agentic.md),
  and separate [ISTIC chapter subproject](subprojects/unesco-book-chapter/README.md).
  The EOI is drafted, not submitted. Recorded demo data remain synthetic even
  after the local cache is replaced with real climate data.

Remaining scientific work: local calibration and crop calendars, electric/diesel
pump shares, hydropower and grid water factors, sensitivity convergence, and
empirical learning/stakeholder validation. Advanced Phase 2/3 components remain
design work with data requirements in the specification, not implemented engines.

---

## 1. Current state

| Area | Status |
|---|---|
| Phase 1 framework (5 agents, 5 scenarios, multi-city, data sources, UI, PDF) | ✅ Done |
| Deterministic nexus coupling + consistency checks | ✅ Done (2026-09-15) |
| LLM robustness (empty-completion retry, Claude provider fix) | ✅ Done, unit-tested only |
| Offline test suite (48 tests) + GitHub Actions CI | ✅ Green |
| README fully in English, with Mermaid architecture diagrams | ✅ Done (2026-09-15) |
| Real LLM run with the new pipeline | ❌ Not yet done |
| Calibration of coupling parameters (`config/nexus.yaml`) | ❌ Placeholders |
| Paper numbers | ⚠️ Any draft numbers from before 2026-09-15 are outdated (see §4) |

---

## 2. What changed on 2026-09-15

### Commits

| Commit | What |
|---|---|
| `f021184` | Code: nexus coupling, LLM fixes, tests + CI (developed on branch `nexus-coupling-fixes`; CI passed, fast-forwarded to `main`, branch deleted) |
| `045fc7e` | Docs: README translated to English, this `PROGRESS.md` added |
| `0f94526` | Docs: ASCII architecture replaced by 3 Mermaid diagrams (system overview, nexus coupling, run lifecycle) |

### Code changes (`f021184`)

A code review found five problem areas; all were fixed.

1. **Correctness bugs**
   - Critic returned empty text (Kimi K2.6 spent all 3000 tokens on reasoning) and the Coordinator synthesized without it. Now: retry once with a doubled budget (cap 16k), then raise `EmptyCompletionError`. Critic `max_tokens` 8000, Coordinator 6000.
   - Claude Agent SDK provider never passed `model`, so runs used the CLI default while reports claimed Opus/Sonnet. Now passes `model`, `tools=[]` (the old `allowed_tools=[]` did **not** disable tools), `max_turns=1`, `setting_sources=[]`; records the model the backend reports.
   - Streamlit ran domain agents sequentially → now parallel via `run_scenario(on_event=...)`.
   - Blocking HTTP calls ran on the event loop → nexus computed in `asyncio.to_thread`; location lookups cached and pinned to the user's geocoding choice.
2. **Nexus coupling** — new `orchestration/nexus.py`, `physics/coupling.py`, `config/nexus.yaml`:
   - climate Δ → Thornthwaite-Mather (now true exponential retention + spin-up) → stress after irrigation → Doorenbos-Kassam yield → production → SSL
   - climate-driven groundwater pumping delta → added electricity demand (ramped to horizon)
   - power-sector water consumption (off-site, reported only)
   - checks: mass balance, seasonal mismatch, groundwater vs surplus, population consistency, yield plausibility, low-confidence inputs
   - `water_stress_fraction` removed from scenarios (derived now; `water_stress_override` for sensitivity runs)
   - Critic/Coordinator receive `key_figures()` + checks; Critic audits number fidelity
3. **Multi-city data**: crop projection needs a local harvest area (BPS or manual override) — no longer borrows Sleman's farmland. World Bank no longer serves `socio.population` (country total). New `GeocodedPopulationSource`. Unknown population → flagged low-confidence fallback.
4. **Engineering**: pytest suite with offline fixture + `FakeProvider`, CI workflow, removed unused deps (polars, xarray, geopandas, shapely), `claude-agent-sdk` moved to `[claude]` extra, deleted empty `analysis/` & `readiness/`, smoke scripts replaced by `scripts/run_scenario.py` (reproducible run records).
5. **Footprint & docs**: model-size classes, PUE, on-site + off-site water, per-provider grid factor. Fixed citation: arXiv:2304.03271 is **Li et al. (2023)**, not "Zhang et al. (2025)". README rewritten to match code (scripted tool pipeline, not LLM tool-calling).

### Documentation changes (`045fc7e`, `0f94526`)

- README is fully English. Indonesian terms are glossed (e.g. LP2B = protected food-crop farmland policy); it notes that agents still write their analyses in formal Indonesian.
- README Architecture section has 3 Mermaid diagrams, render-checked locally with mermaid-cli (light theme only).

---

## 3. Architecture

See the three diagrams in [README → Architecture](README.md#-architecture). In short:

```
scenario ──► compute_nexus()  [deterministic, no LLM]
               tools/ + DataResolver → water balance → coupling → energy → food → checks
                    │  NexusState (key figures + checks + provenance)
                    ▼
            Water ‖ Energy ‖ Food agents (parallel, interpret only)
                    ▼
            Critic (audits narratives vs key figures)
                    ▼
            Coordinator → footprint → run record / PDF / UI
```

Key files: `orchestration/nexus.py` (all numbers), `orchestration/graph.py` (pipeline), `agents/base.py` (retry logic), `config/llm.yaml` (models, budgets, footprint), `config/nexus.yaml` (coupling params).

---

## 4. Result snapshot (synthetic Sleman fixture, 2023 baseline, Mlati)

| Scenario | Stress raw → after irrigation | Deficit mm | Groundwater Mm³/yr | +Pumping GWh | Demand 2030 GWh | Yield t/ha | SSL 2030 |
|---|---|---:|---:|---:|---:|---:|---:|
| S1 BAU | 0.099 → 0.039 | 151 | 7.8 | 0.14 | 2385 | 6.70 | 1.82 |
| S2 JETP | 0.102 → 0.041 | 158 | 8.1 | 0.20 | 2373 | 6.69 | 1.81 |
| S3 Net-Zero | 0.096 → 0.038 | 146 | 7.5 | 0.09 | 2349 | 6.70 | 1.90 |
| S4 Climate Stress | 0.123 → 0.049 | 198 | 10.1 | 0.57 | 2386 | 6.62 | 1.80 |
| S5 Tourism | 0.102 → 0.041 | 158 | 7.8 | 0.19 | 2385 | 6.69 | 1.74 |

Observations to carry into the paper discussion:
- **S4 is now mild for food**: derived stress ≈ 0.05 vs the old hardcoded 0.25, driven by the 60% irrigation-supply assumption and the annual (not growing-season) stress definition.
- **Water→energy link is numerically weak** (≤0.6 GWh vs ~2,400 GWh). Groundwater volume is the more policy-relevant signal.
- Modelled yield 6.7 t/ha vs BPS 6.5 t/ha (3%) — plausible.
- These come from the **synthetic** fixture, not real Open-Meteo data.

---

## 5. Next steps (prioritized)

### Must do before trusting outputs
- [ ] **Real LLM run with the new pipeline**: `python scripts/run_scenario.py S2_JETP_Aligned --provider ollama-cloud`. Confirm the critic is non-empty, check `attempts`/`done_reason` in the run record, and compare timings with the old run.
- [ ] **Live-test the Claude provider** (`--provider claude-agent-sdk`): confirm the reported model matches the requested one and that `CLAUDE_CODE_MAX_OUTPUT_TOKENS` is honoured (only unit-tested so far).
- [x] **Fetch real climate data**: `python -m wef_agentic.data.bootstrap --force`; all five deterministic scenarios rerun in `docs/runs/sweep_openmeteo_20260920.json`. This is not five live LLM runs.
- [ ] **Calibrate `config/nexus.yaml` `ASSUMPTION` values**: irrigation supply fraction, groundwater share, pump head/efficiency, cropping intensity. Sources to chase: Distan Sleman, BBWS Serayu-Opak, PLN UP3 Yogyakarta. Note that diesel pumps are common and their energy is not grid demand.
- [x] Archived the obsolete May run in `docs/runs/archive/` with an explanatory note.

### Modelling improvements
- [ ] Growing-season stress (rice months / 2–3 seasons) instead of annual `1 − ETa/PET`; revisit the S4 narrative.
- [x] Historical-year selection via `--baseline-year` in scenario and sweep scripts; 2015 regression covered.
- [x] Pumping now compares baseline physical area with horizon physical area; land-loss regression passes.
- [ ] Hydropower/PLTMH water dependence not modelled; Indonesian grid water intensity (EWIF) missing, so local-run off-site water is reported as missing.
- [x] Sobol tooling for irrigation/power-water parameters, explicit bounds and saved samples/results. Scientific convergence and defensible bounds remain open.

### Code / housekeeping
- [x] Streamlit migrated to `width="stretch"`; startup and recorded demo checked.
- [x] Retain current Claude model defaults for reproducibility; validated live on this machine.
- [ ] Optional: native LLM tool-calling (registry already has JSON schemas). Keep numbers deterministic if you do.
- [ ] Check the README Mermaid diagrams in GitHub dark mode (only the light theme was checked).
- [ ] Phase 2 roadmap: Policy + Stakeholder agents, SWAT+/OSeMOSYS/AquaCrop, CMIP6 ensemble, MCDA, paper v0.1.

---

## 6. How to resume

```bash
cd ~/Desktop/Projects/wef-agentic
source .venv/bin/activate              # Python 3.11 venv (gitignored; recreate: uv venv -p 3.11 .venv && uv pip install -e ".[dev,claude]")
pytest                                 # ~15s, offline
ruff check src tests scripts
python scripts/generate_fixture.py     # if data/processed/ is empty
streamlit run src/wef_agentic/ui/streamlit_app.py
python scripts/run_scenario.py S2_JETP_Aligned [--location Bandung] [--provider ollama-local --model gemma4:e4b]
```

Rendering README diagrams locally (uses the installed Google Chrome, no Chromium download):

```bash
echo '{"executablePath": "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "args": ["--no-sandbox"]}' > /tmp/pp.json
PUPPETEER_SKIP_DOWNLOAD=1 npx -y @mermaid-js/mermaid-cli@11 -p /tmp/pp.json -i diagram.mmd -o diagram.png -b white -s 2
```

Environment notes:
- `.env` needs `OLLAMA_API_KEY` for ollama-cloud; the Claude provider uses the logged-in Claude Code CLI.
- The repo has **no local git identity**; commit with `git -c user.name="Zulfikar Aji Kusworo" -c user.email="greataji13@gmail.com" commit ...`.
- `gh` is authenticated as `zakusworo` (keyring). Node 22 is available for `npx`.

## 7. Conventions

- Commits are authored by the user only — **no Claude co-author trailer**.
- Code changes: work on a branch, wait for CI to pass, fast-forward merge to `main`, delete the branch. Docs-only changes may go straight to `main`.
- Numbers come from `compute_nexus`, never from LLM output. New physics goes in `physics/`, cross-sector glue in `orchestration/nexus.py`, parameters in `config/nexus.yaml` with a source or an `ASSUMPTION` tag.
- When the pipeline or coupling changes, update the README Mermaid diagrams and render-check them.
