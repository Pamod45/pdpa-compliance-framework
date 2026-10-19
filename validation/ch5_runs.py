"""
Chapter 5 evidence runs: reproducibility + NIST example SSP, on the v1.1 method of record.

Run from the repo root with the venv active:
    python validation/ch5_runs.py

What it does
  1. Checks config/pcef_params.json is the frozen v1.1 file (fingerprint debb78cfde93).
     Stops if not, so nothing is reported from the wrong config.
  2. Runs the full pipeline 3 times on FleetTrack and 2 times on the NIST example SSP.
  3. Compares the repeated runs, ignoring only the run timestamp and output path.
  4. Writes outputs/ch5/ch5_summary.md and ch5_summary.json.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

V11 = "debb78cfde93"
OUT = Path("outputs/ch5")
SSPS = {
    "fleettrack": ("data/raw/ssps/fleettrack/fleettrack_ssp.json", 3),
    "nist_example": ("data/raw/ssps/public/nist_example/enterprise_logging_auditing_ssp.json", 2),
}
VOLATILE = {"run_at_utc", "argv"}


def sha(p: str) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def strip(o):
    if isinstance(o, dict):
        return {k: strip(v) for k, v in o.items() if k not in VOLATILE}
    if isinstance(o, list):
        return [strip(v) for v in o]
    return o


def numbers(o, path=""):
    """Flatten every numeric leaf to {path: value} so runs can be diffed value by value."""
    if isinstance(o, dict):
        for k, v in o.items():
            yield from numbers(v, f"{path}/{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from numbers(v, f"{path}[{i}]")
    elif isinstance(o, (int, float)) and not isinstance(o, bool):
        yield path, float(o)


def main() -> None:
    fp = sha("config/pcef_params.json")[:12]
    print(f"config fingerprint: {fp}")
    if fp != V11:
        sys.exit(f"STOP: config/pcef_params.json is not v1.1 ({fp} != {V11}). "
                 "Restore the v1.1 config (git checkout <v1.1 tag or commit> -- config/) and rerun.")
    OUT.mkdir(parents=True, exist_ok=True)
    summary = {"config_fingerprint": fp, "ssps": {}}
    for name, (ssp, n) in SSPS.items():
        runs, secs = [], []
        for i in range(1, n + 1):
            out = OUT / f"{name}_run{i}"
            t = time.perf_counter()
            subprocess.run([sys.executable, "-m", "pcef.pipeline.run", "--all", "--embedder", "sbert",
                            "--ssp", ssp, "--out", str(out)], check=True)
            secs.append(round(time.perf_counter() - t, 1))
            runs.append(json.loads((out / "run.json").read_text(encoding="utf-8")))
        base = strip(runs[0])
        base_nums = dict(numbers(base))
        identical, max_diff = [], 0.0
        for r in runs[1:]:
            s = strip(r)
            identical.append(s == base)
            for k, v in numbers(s):
                max_diff = max(max_diff, abs(v - base_nums.get(k, float("nan"))) if k in base_nums else float("inf"))
        pairs = runs[0]["pairs"]
        scored = [p for p in pairs if p["status"] == "scored"]
        summary["ssps"][name] = {
            "runs": n, "seconds_per_run": secs,
            "all_identical": all(identical), "max_abs_numeric_diff": max_diff,
            "pairs_total": len(pairs), "pairs_scored": len(scored),
            "excluded_by": {k: sum(1 for p in pairs if p.get("excluded_by") == k)
                            for k in {p.get("excluded_by") for p in pairs if p["status"] != "scored"}},
            "role_source": runs[0]["provenance"].get("system_roles"),
            "tuples": [{"pair": f"{p['unit_id']}|{p['control_id']}", **p["tuple"]} for p in scored],
        }
    (OUT / "ch5_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    lines = [f"# Chapter 5 runs (config {fp})", "",
             "| SSP | runs | identical | max numeric diff | pairs | scored | seconds/run |", "|---|---|---|---|---|---|---|"]
    for k, s in summary["ssps"].items():
        lines.append(f"| {k} | {s['runs']} | {s['all_identical']} | {s['max_abs_numeric_diff']:.2e} | "
                     f"{s['pairs_total']} | {s['pairs_scored']} | {s['seconds_per_run']} |")
    (OUT / "ch5_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()