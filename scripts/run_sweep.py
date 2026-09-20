"""Save deterministic results for all five scenarios without LLM calls."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from wef_agentic.config.settings import PROCESSED_DIR, load_nexus_config
from wef_agentic.orchestration import compute_nexus, get_scenario
from wef_agentic.orchestration.scenarios import SCENARIOS


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-year", type=int, default=2023)
    parser.add_argument("--growing-months", nargs="+", type=int)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    results = []
    for name in SCENARIOS:
        scenario = get_scenario(name)
        scenario["water_baseline_year"] = args.baseline_year
        if args.growing_months is not None:
            scenario["growing_months"] = args.growing_months
        nexus = compute_nexus(scenario)
        results.append({"id": name, "scenario": scenario, "nexus": nexus.to_dict()})
        print(name, nexus.coupling["water_stress_effective"], flush=True)
    record = {
        "created_at": datetime.now(UTC).isoformat(),
        "kind": "deterministic-only; no LLM validation",
        "git_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "git_dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], text=True)),
        "config": load_nexus_config(),
        "climate_files_sha256": {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(PROCESSED_DIR.glob("openmeteo_sleman_*.parquet"))
        },
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
