# Evidence inventory, 20 September 2026

## Runs

- [Synthetic deterministic sweep](../../../docs/runs/sweep_synthetic_20260920.json): all five scenarios.
- [Synthetic live Claude run](../../../docs/runs/run_S2_JETP_Aligned_sleman_claude-agent-sdk_20260920_143021.json): S2, 210.66 seconds.
- [Real-climate deterministic sweep](../../../docs/runs/sweep_openmeteo_20260920.json): five scenarios, 2023 climate baseline.
- [Historical-year comparison](../../../docs/runs/sweep_openmeteo_2015_20260920.json): five scenarios, 2015 climate baseline.
- [Real-climate live Claude run](../../../docs/runs/run_S2_JETP_Aligned_sleman_claude-agent-sdk_20260920_144208.json): S2, 200.26 seconds.
- [Sobol smoke run](../../../docs/runs/sensitivity_synthetic_smoke_20260920.json): 56 evaluations on synthetic climate, illustrative bounds; not a convergence study.

Both live runs returned five nonempty narratives, all first-attempt completions
with `stop`. No deterministic check failed in the real-climate S2 run. Seasonality
and low-confidence warnings remain. Completion is not proof that every narrative
claim is correct; manual claim-by-claim review remains necessary before publication.

## Verification

- 59 offline tests pass on Python 3.14.7; lint passes.
- Streamlit recorded-demo startup verified with AppTest.
- Chromium: dashboard and six chart containers rendered; tabs responded; PDF
  downloaded successfully; no document-level overflow at 390-pixel width.
- Three Mermaid diagrams rendered in default and dark themes. Native GitHub
  rendering was not inspected.
- EOI abstract: 231 whitespace-delimited words; rendered PDF: one A4 page.
  DOCX content was generated from the same abstract. LibreOffice rendering failed
  on this host, so the PDF was generated independently with ReportLab and inspected.

## Interpretation limits

Downloaded climate is not synthetic, but irrigation, pump and crop assumptions
remain uncalibrated. The historical-year comparison combines baseline choice with
the same scenario deltas; it is not an attribution study. No learning assessment,
stakeholder workshop, policy adoption or predictive validation has been conducted.
Do not present the software regression count as scientific validation.

`climate-download-manifest.json` identifies local data files by checksum;
`figure-manifest.json` links figure exports to saved records. Local cache files are
gitignored. Keep the recorded demo snapshot when refreshing caches.
