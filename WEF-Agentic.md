# WEF-Agentic project specification

Version 0.1, 20 September 2026. Created from the repository and the user's request
to replace the unavailable internal specification. This is a new working design,
not a recovered document. Proposed capabilities below are not claims of implementation.

## Purpose and boundary

Support comparison of water, energy and food scenarios at regency/city scale,
starting with Sleman. Compute quantities with deterministic models; use language
models to interpret results, identify inconsistencies and explain trade-offs.
Outputs support research and deliberation. They do not authorize infrastructure,
allocate water, or speak for stakeholders.

The current study compares five scenarios: business as usual, JETP-aligned,
net-zero, climate stress and tourism growth. Scenario names containing SSP labels
currently denote illustrative climate deltas, not downloaded CMIP6 projections.
Hazard and tourism narratives must not be described as quantified impacts unless
an explicit model calculates them.

## Implemented foundation

The implementation is in [src/wef_agentic](src/wef_agentic). The
[README](README.md) describes operation; [PROGRESS.md](PROGRESS.md) records validation.

1. Resolve a location and inputs through manual, BPS, climate, gazetteer,
   World Bank and country-default sources. Preserve provenance and confidence.
2. Compute monthly Thornthwaite–Mather water balance, derive crop water stress,
   project yield/area/food self-sufficiency, calculate pumping changes and energy
   demand, and report power-sector water consumption.
3. Run consistency checks before narrative generation.
4. Run Water, Energy and Food agents concurrently, then Critic and Coordinator.
5. Save run records, footprint estimates and reports; expose results in Streamlit.

Growing-month selection is optional. Until a calendar is sourced, the default is
annual stress. Selecting several seasons' months produces a combined PET-weighted
stress value; it does not implement crop-stage yield response or distinguish crops
with different calendars. Baseline pumping uses baseline land area; scenario
pumping uses projected land area. Pump energy assumes electric pumps, so applying
it to diesel installations is an unresolved calibration limitation.

## Scientific invariants

- Every quantity has a unit, time interval, spatial boundary and source. Missing
  observations remain missing or explicitly flagged proxies.
- Synthetic data are for software verification. Real climate data are reanalysis
  inputs, not proof of local calibration or independent validation.
- LLM narratives cannot overwrite computed values. Critic disagreement must be
  retained in the run record and synthesis.
- Conserve water within the stated balance. Separate consumptive use from
  withdrawals and local water from off-site generation water.
- Compare baseline/scenario values over compatible units, areas and periods.
  Do not sum annual harvest area across seasons and then treat it as physical area.
- Record all scenario overrides, model/solver versions, input hashes, code revision,
  random seeds and calibration choices. Mark runs produced from a dirty checkout.
- Separate measured uncertainty, assumed parameter ranges, climate-model spread
  and variation between LLM narratives.

## Required study inputs

No local calibrated SWAT+, OSeMOSYS, AquaCrop or CMIP6 study package was supplied.
Creating this specification does not supply those datasets.

| Input | Required content | Candidate source / status |
|---|---|---|
| Study boundary | Administrative polygon, catchments, irrigation command areas; CRS and version | Local GIS / BBWS; to collect |
| Climate | Daily precipitation, temperature, ET0 and auxiliary weather; station/grid metadata | Open-Meteo archive; bootstrap implemented |
| Water observations | Discharge, groundwater levels, irrigation delivery, abstraction and seasonality | BBWS Serayu-Opak / local irrigation agencies; to collect |
| Pumps | Electric/diesel shares, head, efficiency, operating hours and metered energy | Field survey / Distan / PLN; to collect |
| Agriculture | Physical irrigated area, annual harvest area, yield, planting/harvest dates, cultivar and soil | BPS / Distan / field observations; partial static inputs only |
| Energy | Demand by year/sector, technology fleet, capacity, costs, fuel, emissions and dispatch constraints | PLN / published planning datasets; to collect |
| Stakeholders | Participants, consent, objectives, weights, disagreements and evidence | Workshop; not conducted |

An acquisition manifest must identify publisher, URL/file, retrieval date, licence,
coverage, units, checksum, processing and gaps. Keep raw files separate from
processed inputs. The BPS [Sleman rice and agricultural machinery publication](https://slemankab.bps.go.id/id/publication/2025/07/30/4781b70f60cc8942c9fbae0a/produksi-padi-dan-alat-mesin-pertanian-kabupaten-sleman-2020-2024.html)
is an acquisition lead, not evidence for pump efficiency or irrigation delivery.

## Phase 2: implementation contracts

### External model adapters

Proposed location: `src/wef_agentic/models/`. Each adapter accepts a validated
manifest, scenario and output directory; returns quantities, provenance,
diagnostics and artefact paths. It must fail explicitly for missing inputs,
incompatible versions, non-convergence or invalid outputs. Engine executables and
study files are configured separately from Python code.

| Adapter | Inputs | Normalized outputs | Acceptance |
|---|---|---|---|
| SWAT+ | Calibrated basin project, weather, soils, land cover and management | Monthly flow, ET, recharge and storage with basin/HRU identifiers | Reference-project reproduction, parser tests, mass balance and held-out discharge validation |
| OSeMOSYS | Demand, time slices, technologies, capacities, costs, fuels and constraints | Generation, capacity, fuel, cost, emissions and unmet demand | Optimal solver status, energy balances and a published benchmark |
| AquaCrop | Weather, crop, soil, planting and management files | Seasonal biomass, yield, ET and irrigation demand | Reference-case reproduction and held-out local yields |

SWAT+ has versioned output formats; pin a version and parse units/header metadata,
not guessed column positions ([official output format](https://swatplus.gitbook.io/io-docs/swat%2B-output-files/output-file-format)).
OSeMOSYS needs both model code and a study data file; solver installation alone is
insufficient ([official manual](https://github.com/OSeMOSYS/OSeMOSYS/blob/master/docs/manual/Create%20a%20model%20in%20OSeMOSYS.rst)).
AquaCrop requires climate, crop, soil and management information
([FAO input requirements](https://www.fao.org/aquacrop/overview/input-requirements/)).

Start with one-way coupling and a documented baseline. A later iterative coupling
must define exchanged variables, time aggregation, convergence tolerances and
failure conditions before execution. Do not introduce circular feedback silently.

### Hydropower and electricity water use

Add a separate hydropower module only with flow, environmental-flow requirements,
head, efficiency, capacity and operating rules. Report generation constrained by
available flow and capacity. Treat reservoir evaporation separately from turbine
throughput. National/grid water intensity requires a sourced generation mix and
compatible technology/cooling consumption factors; keep it missing until available.

### CMIP6 ensemble

Discover datasets through [ESGF / WCRP](https://wcrp-cmip.org/cmip-data-access/).
The acquisition manifest records source ID, experiment, member, grid, variable,
frequency, version, calendar, checksum and citation. Select historical and future
periods explicitly; match historical/scenario members and report exclusions.

Implement calendar-aware unit conversion, spatial extraction and comparison with
the observed/reanalysis reference period. Specify a bias-adjustment method and
validation period before producing adjusted projections. Preserve each member's
outputs and report spread; do not present an ensemble mean as a probability forecast.
Acceptance requires unit/calendar tests, reproducible acquisition and per-member
coverage checks. No model list or local correction has yet been selected.

### Sensitivity and MCDA

Sobol tooling is available in [scripts/run_sensitivity.py](scripts/run_sensitivity.py).
The [example bounds](docs/sensitivity-example.json) are illustrative independent
uniform ranges, not calibrated distributions. Report first/total indices and
confidence intervals; repeat at increasing sample counts before interpreting ranks.
Constant outputs have undefined indices. Implementation follows
[SALib's documented sampling and analysis pairing](https://salib.readthedocs.io/en/main/api/SALib.analyze.html).

Proposed MCDA accepts an alternatives-by-criteria matrix with units, benefit/cost
direction, normalization, missing-data policy and explicitly supplied weights.
Report raw values alongside normalized scores. Require non-negative weights summing
to one and sensitivity to weight changes. Equal weights may be an explicitly
labelled exploratory case; they do not represent stakeholder preferences.

### Policy and stakeholder agents

Add a Policy agent and four perspective agents (Farmer, Local Government, PLN,
Community) after defining structured outputs and evidence inputs. These are
simulated perspectives until real participants validate them.

Each output must contain claims linked to evidence IDs, objectives, constraints,
trade-offs, affected groups, uncertainties and questions for participants. Pass the
same deterministic results to all agents. Policy claims need dated primary documents;
unknown policy status stays unknown. Critic checks numerical and source fidelity.
Do not invent quotations, consent, community preferences or institutional endorsement.

Acceptance: fake-provider contract tests, contradictory-evidence cases, missing-source
cases, a complete live run, and human review of one study case. Native tool-calling
remains optional; expose only read-only validated tools, constrain calls/time/cost,
and retain the deterministic calculation path as the source of reported numbers.

## Phase 3 and publications

Workshop preparation can proceed as a protocol and materials. Completion requires
actual recruitment, consent, recorded deliberation and participant validation.
No agent-generated dialogue may count as workshop evidence.

BMKG/BPS live adapters require confirmed endpoints, access credentials where
applicable, data licences, schema checks, caching and stale-data handling. Store
credentials outside version control; test adapters with recorded non-sensitive fixtures.

Paper v0.1 can report a reproducible methods/software study once input provenance,
validation and sensitivity are documented. Local policy conclusions require local
calibration. Paper v1.0 additionally requires the planned stakeholder evidence.
Select a venue before enforcing a submission template. Every reported table must
trace to a saved run; include limitations and failed/excluded cases.

## Delivery sequence and completion rules

1. Finish Phase 1 regression checks, live-provider validation and real-climate runs.
2. Collect and audit calibration inputs; define held-out validation before fitting.
3. Implement each external adapter against one reproducible reference project.
4. Add ensemble and uncertainty experiments; verify convergence and comparability.
5. Add policy/perspective agents and MCDA with traceable evidence and weights.
6. Conduct the workshop and prepare the appropriate manuscript.

Code, data acquisition, calibration, empirical validation and publication are distinct
deliverables. Mark each complete only with its evidence in `PROGRESS.md`. A working
adapter without a local study is not a calibrated model; a design document is not
an implemented Phase 2.
