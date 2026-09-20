# Draft captions and limits

1. **Seasonal water balance in the S2 demonstration.** Monthly precipitation,
   reference evapotranspiration and modelled deficit use the synthetic Mlati 2023
   fixture under the S2 climate deltas. These are software-demonstration outputs,
   not measured weather or a calibrated climate projection.
2. **Comparison of five illustrative scenarios.** Water stress, change in pumping
   energy, and rice self-sufficiency follow the recorded deterministic calculations.
   S1: business as usual; S2: JETP-aligned; S3: net-zero; S4: climate stress; S5:
   tourism growth. S3 has a 2045 horizon while the other scenarios use 2030; pumping
   changes refer to each scenario's horizon, whereas self-sufficiency is evaluated
   at 2030. This figure illustrates model behaviour, not a like-for-like policy ranking.
3. **Agent execution times in one live Claude run.** Domain agents run concurrently,
   followed by Critic and Coordinator. Bars are individual elapsed times and must
   not be summed as end-to-end runtime. This is one observed execution, not a
   performance benchmark or model comparison.
4. **Architecture and nexus coupling diagrams.** Exported from the application's
   README. They describe the implemented screening workflow; advanced Phase 2
   engines are not implemented by these diagrams.
5. **Demo screenshot.** Recorded Claude narratives and synthetic model outputs in
   the local Streamlit application. The screenshot demonstrates interface behaviour,
   not learning effectiveness.

Use `figure-manifest.json` and `synthetic-scenario-metrics.csv` in `../evidence/`
to trace exported plots to saved inputs. Prefer vector PDF/SVG for the chapter;
PNG exports are 300 dpi. Final placement and formatting depend on editorial guidance.

**Additional real-climate experiment (fig04).** Water stress across five scenarios
using downloaded Open-Meteo climate for historical baseline years 2023 and 2015.
Each series applies the same scenario-specific climate deltas and uncalibrated
irrigation assumptions. Differences illustrate baseline-year sensitivity, not a
validated causal estimate of ENSO or future climate risk. Neither series is a
synthetic fixture. The figure does not establish local predictive accuracy.
