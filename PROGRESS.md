# WEF-Agentic — Progress Log

_Last updated: 2026-09-15 · `main` @ `f021184` · CI green_

Handoff notes for the next working session. README describes *what the framework is*; this file tracks *where the work stands* and *what to do next*.

---

## 1. Current state

| Area | Status |
|---|---|
| Phase 1 framework (5 agents, 5 scenarios, multi-city, data sources, UI, PDF) | ✅ Done |
| Deterministic nexus coupling + consistency checks | ✅ Done (2026-09-15) |
| LLM robustness (empty-completion retry, Claude provider fix) | ✅ Done, unit-tested only |
| Offline test suite (48 tests) + GitHub Actions CI | ✅ Green |
| Real LLM run with the new pipeline | ❌ Not yet done |
| Calibration of coupling parameters (`config/nexus.yaml`) | ❌ Placeholders |
| Paper numbers | ⚠️ Any draft numbers from before 2026-09-15 are outdated (see §4) |

---

## 2. What changed in the 2026-09-15 session (commit `f021184`)

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

---

## 3. Architecture in one picture

```
scenario ──► compute_nexus()  [deterministic, no LLM]
               tools/ + DataResolver → water balance → coupling → energy → food → checks
                    │  NexusState (key_figures + checks + provenance)
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
- [ ] **Replace the synthetic fixture with real climate data**: `python -m wef_agentic.data.bootstrap`, then re-run all 5 scenarios.
- [ ] **Calibrate `config/nexus.yaml` `ASSUMPTION` values**: irrigation supply fraction, groundwater share, pump head/efficiency, cropping intensity. Sources to chase: Distan Sleman, BBWS Serayu-Opak, PLN UP3 Yogyakarta. Note that diesel pumps are common and their energy is not grid demand.
- [ ] Delete or archive `docs/runs/run_S2_JETP_Aligned_deepseek_cloud_20260517_110212.json` (pre-coupling, empty critic).

### Modelling improvements
- [ ] Growing-season stress (rice months / 2–3 seasons) instead of annual `1 − ETa/PET`; revisit the S4 narrative.
- [ ] Drought-year selection (e.g. 2015/2019 El Niño) instead of only a delta on 2023.
- [ ] Pumping uses horizon irrigated area for both scenario and baseline, so the land-loss effect on pumping is ignored.
- [ ] Hydropower/PLTMH water dependence not modelled; Indonesian grid water intensity (EWIF) missing, so local-run off-site water is reported as missing.
- [ ] Sobol sensitivity on `nexus.yaml` parameters (Phase 2 roadmap).

### Code / housekeeping
- [ ] Streamlit `use_container_width` is deprecated (removal date passed): switch to `width="stretch"`.
- [ ] Decide whether to update `model_claude` in `llm.yaml` (currently `claude-opus-4-7` / `claude-sonnet-4-6`; newer Claude 5 models exist). This changes reproducibility vs earlier runs.
- [ ] Optional: native LLM tool-calling (registry already has JSON schemas). Keep numbers deterministic if you do.
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

Environment notes:
- `.env` needs `OLLAMA_API_KEY` for ollama-cloud; the Claude provider uses the logged-in Claude Code CLI.
- The repo has **no local git identity**; commit with `git -c user.name="Zulfikar Aji Kusworo" -c user.email="greataji13@gmail.com" commit ...`.
- `gh` is authenticated as `zakusworo` (keyring).

## 7. Conventions

- Commits are authored by the user only — **no Claude co-author trailer**.
- Work on a branch, wait for CI to pass, fast-forward merge to `main`, delete the branch.
- Numbers come from `compute_nexus`, never from LLM output. New physics goes in `physics/`, cross-sector glue in `orchestration/nexus.py`, parameters in `config/nexus.yaml` with a source or an `ASSUMPTION` tag.
