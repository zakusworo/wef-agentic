# Real-climate sensitivity convergence check

26 September 2026. S2, Sleman, 2023 Open-Meteo baseline; seed 42; existing illustrative independent uniform bounds in `docs/sensitivity-example.json`. The grid-electric pumped-volume share is fixed at the uncalibrated default of 1.0.

Completed N=16, 32 and 64 (112 + 224 + 448 = 784 model evaluations). Larger N=128/256 runs were interrupted to shorten the work at the user’s request. Input hashes, scenarios and base configurations match across the completed runs.

| Output | Largest S1 change, N32 to N64 | Largest ST change, N32 to N64 | Largest ST confidence half-width at N64 |
|---|---:|---:|---:|
| water_stress | 0.0006 | 0.0001 | 0.2692 |
| pumping_delta_gwh | 0.1164 | 0.0181 | 0.2735 |
| power_water_m3 | 0.1164 | 0.0181 | 0.2735 |
| yield_t_ha | 0.0006 | 0.0001 | 0.2692 |

This small ladder does not establish convergence: confidence intervals remain wide, and first-order pumping indices still move materially. Estimates above one or below zero at small N are retained as estimator uncertainty, not interpreted as physical shares.

Within these bounds, only irrigation supply fraction changes water stress and yield; the other sampled parameters act on pumping. Pumping and power-water indices coincide because the power-water output is an affine function of pumping electricity when the generation mix and water factors are fixed. These rankings are conditional on the selected bounds and do not validate local parameter values.

Next: source defensible local bounds and dependencies, then repeat at increasing N with acceptance criteria defined before interpreting rankings. Do not use this exploratory check as calibrated uncertainty or policy evidence.

Records:

- [N=16](runs/sensitivity_openmeteo_20260926_n16.json)
- [N=32](runs/sensitivity_openmeteo_20260926_n32.json)
- [N=64](runs/sensitivity_openmeteo_20260926_n64.json)
