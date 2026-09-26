"""Sobol analysis of nexus parameters using explicitly supplied uniform bounds.

Bounds JSON: {"irrigation.supply_fraction": [0.3, 0.8], ...}.
Bounds are study assumptions; this script does not calibrate them.
Install with pip install -e '.[sensitivity]'.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from SALib.analyze import sobol as analyze
from SALib.sample import sobol as sample

from wef_agentic.config.settings import PROCESSED_DIR, load_nexus_config
from wef_agentic.orchestration import compute_nexus, get_scenario
from wef_agentic.orchestration.runlog import git_revision


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bounds", type=Path, required=True)
    parser.add_argument("--scenario", default="S2_JETP_Aligned")
    parser.add_argument("--samples", type=int, default=128)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--baseline-year", type=int, default=2023)
    parser.add_argument("--growing-months", type=int, nargs="+")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.samples < 2 or args.samples & (args.samples - 1):
        parser.error("--samples must be a power of two >= 2")
    bounds = json.loads(args.bounds.read_text())
    base = load_nexus_config()
    if not bounds:
        parser.error("at least one parameter bound is required")
    for name, interval in bounds.items():
        section, key = name.split(".", 1)
        if section not in ("irrigation", "power_sector_water") or key not in base[section]:
            parser.error(f"unsupported parameter: {name}")
        if len(interval) != 2 or not all(np.isfinite(interval)) or interval[0] >= interval[1]:
            parser.error(f"invalid bounds: {name}")
    problem = {"num_vars": len(bounds), "names": list(bounds), "bounds": list(bounds.values())}
    samples = sample.sample(problem, args.samples, calc_second_order=False, seed=args.seed)
    outputs = []
    scenario = get_scenario(args.scenario)
    scenario["water_baseline_year"] = args.baseline_year
    if args.growing_months is not None:
        scenario["growing_months"] = args.growing_months
    for row in samples:
        config = copy.deepcopy(base)
        for name, value in zip(bounds, row, strict=True):
            section, key = name.split(".", 1)
            config[section][key] = float(value)
        nexus = compute_nexus(scenario, config=config)
        outputs.append([
            nexus.coupling["water_stress_effective"],
            nexus.coupling["extra_pumping_demand_gwh"],
            nexus.coupling["power_sector_water_m3_2030"],
            nexus.crop_projection["endpoints"]["yield_t_ha"],
        ])
    values = np.asarray(outputs)
    indices = {}
    names = ["water_stress", "pumping_delta_gwh", "power_water_m3", "yield_t_ha"]
    for column, name in enumerate(names):
        y = values[:, column]
        if np.ptp(y) == 0:
            indices[name] = {"status": "constant output; indices undefined"}
        else:
            result = analyze.analyze(problem, y, calc_second_order=False, seed=args.seed)
            indices[name] = {key: result[key].tolist() for key in ("S1", "S1_conf", "ST", "ST_conf")}
    record = {"created_at": datetime.now(UTC).isoformat(), "git": git_revision(),
              "climate_files_sha256": {
                  path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                  for path in sorted(PROCESSED_DIR.glob("openmeteo_sleman_*.parquet"))
              },
              "scenario": scenario, "base_config": base, "problem": problem,
              "seed": args.seed, "base_samples": args.samples, "evaluations": len(samples),
              "input_samples": samples.tolist(), "output_names": names,
              "outputs": outputs, "indices": indices,
              "note": "Uniform independent bounds supplied by caller; not calibrated probabilities."}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
