# Calibration input audit

Audit date: 26 September 2026. This inventories the local checkout; it does not
establish that the missing observations are unavailable from their publishers.

## Available locally

- Open-Meteo daily 1991–2024 climate cache and monthly/annual aggregates in
  `data/processed/`, plus a NASA POWER cache.
- Static Sleman population, harvest-area, yield and electricity inputs in
  `src/wef_agentic/data/bps_static.py`. These are not pump or irrigation observations.
- Recorded real-climate scenario runs and deterministic sweeps in `docs/runs/`.
- No study-input files in `data/external/` or `data/raw/` beyond `.gitkeep`.

## Inputs needed before changing screening defaults

| Parameter or task | Required observations | Acceptance before use |
|---|---|---|
| Irrigation supply fraction | Monthly delivered irrigation volume, command area and gross demand for the same area and period | Reconcile delivery boundary, conveyance losses and units; reserve separate validation years |
| Groundwater share | Surface-water and groundwater deliveries by month and command area | Use volume shares, not pump counts; document missing abstractions |
| Pump head and efficiency | Dynamic head, flow, measured electricity/fuel, operating hours and pump type | Separate electric and diesel equipment; establish energy-weighted representative values |
| Electric/diesel split | Pump inventory linked to pumped volumes or measured energy | Do not equate equipment-count shares with energy shares; diesel energy must not become grid demand |
| Cropping intensity | Physical irrigated area and annual harvested area with matching geography and year | Document multiple harvests; do not use harvest area as physical area |
| Growing-season stress | Planting/harvest dates by crop, season and irrigation area | Existing `--growing-months` supports a combined PET-weighted window; separate crop-stage responses are not implemented |
| Hydropower | Flow series, environmental-flow requirement, head, efficiency, capacity and operating rules | Validate generation against observed output; separate turbine flow from consumptive losses |
| Indonesian grid water intensity | Dated generation mix and compatible technology/cooling water-consumption factors | Preserve freshwater/seawater and withdrawal/consumption distinctions; keep missing until supported |
| Sobol interpretation | Justified parameter bounds, dependence assumptions and measured uncertainty | Check increasing sample sizes and rank/interval stability; example bounds are not calibrated probabilities |

Candidate holders already identified in the project specification are Distan
Sleman, BBWS Serayu-Opak and PLN. No requests have been sent to them.

## Acquisition and validation procedure

1. Store source files separately from processed inputs. Record publisher, original
   URL or file identifier, retrieval date, licence, spatial/temporal coverage,
   units, checksum and processing steps.
2. Audit missing values and overlapping boundaries before fitting any parameter.
3. Select calibration and held-out validation periods before fitting; record the
   target metrics and acceptance criteria without using the held-out outcomes.
4. Change `config/nexus.yaml` only with a documented estimate and source. Retain
   an assumption label for unsupported parameters.
5. Rerun all five deterministic scenarios and sensitivity analysis. Publish the
   unresolved warnings with the results, and reassess the S4 narrative using the
   sourced crop calendar.

The software checks and complete LLM responses do not establish scientific
calibration, learner outcomes or stakeholder agreement.
