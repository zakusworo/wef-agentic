# ISTIC book-chapter subproject

Target: *Artificial Intelligence for Climate Learning and Sustainable Development*,
ISTIC under the auspices of UNESCO and Universitas Negeri Malang; planned Springer
Nature (Singapore) edited volume, 2027.

**EOI deadline: 21 September 2026.** The call does not state a deadline timezone.
Submit before the final day where possible. Full-chapter guidelines and deadlines
will be supplied to selected contributors. No acceptance is implied by this folder.

## Working files

- [Fit assessment](proposal/fit-assessment.md)
- [EOI title, author fields and abstract](proposal/EOI.md)
- Submission copies: [DOCX](proposal/EOI-Zulfikar-Aji-Kusworo.docx) and
  [PDF](proposal/EOI-Zulfikar-Aji-Kusworo.pdf), with a 231-word abstract
- [Email draft](proposal/email-draft.txt), not sent
- [Chapter outline and evaluation plan](manuscript/outline.md)
- [Figure captions and evidence limits](figures/CAPTIONS.md)
- [Supplied call](source/Call-for-contribution_08092026.PDF)
- [Application specification](../../WEF-Agentic.md)

The application demo runs at http://127.0.0.1:8501. Restart from the repository root
with `bash scripts/start_demo.sh`. It replays an actual Claude run using a synthetic
climate fixture. Replay makes no new LLM calls; Run Scenario does.

Regenerate exported demo figures from the repository root:

```bash
.venv/bin/python subprojects/unesco-book-chapter/scripts/export_figures.py
```

The chapter subproject consumes recorded application outputs. It does not maintain
a second physics implementation. Synthetic software-demonstration figures must not
be presented as measured Sleman conditions or calibrated projections. Keep real-data
experiments in separately named files with their acquisition and parameter provenance.

EOI status: draft prepared with confirmed author details; no email sent.
