"""
Build the fixed expert-panel pack: the shortlisted pairs, identical for every expert.

  python validation/build_panel_pack.py

Inputs : outputs/run_method_of_record_v1_1/run.json (PCEF, v1.1), outputs/llm_chat/calls.jsonl,
         outputs/llm_chat/llm_analysis.json (shortlist).
Output : outputs/panel/panel_items.json  (order fixed with a seeded shuffle, so no grouping by clause)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.enrich import pair_context  # noqa: E402

SEED = 20261005


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-json", default="outputs/run_method_of_record_v1_1/run.json")
    ap.add_argument("--calls", default="outputs/llm_chat/calls.jsonl")
    ap.add_argument("--analysis", default="outputs/llm_chat/llm_analysis.json")
    ap.add_argument("--out", default="outputs/panel/panel_items.json")
    a = ap.parse_args(argv)
    run = json.loads((ROOT / a.run_json).read_text(encoding="utf-8"))
    ana = json.loads((ROOT / a.analysis).read_text(encoding="utf-8"))
    short = list(dict.fromkeys(d["pair"] for ax in ("alignment", "realization") for d in ana["shortlist"][ax]))
    calls = [json.loads(l) for l in (ROOT / a.calls).read_text(encoding="utf-8").splitlines() if l.strip()]
    llm = defaultdict(lambda: defaultdict(list))
    for c in calls:
        if c.get("parsed"):
            llm[c["pair"]][c["provider"]].append({"run": c["run"], **c["parsed"], "model": c.get("served_model")})
    pairs = {f"{p['unit_id']}|{p['control_id']}": p for p in run["pairs"] if p["status"] == "scored"}
    items = []
    for pid in short:
        p = pairs[pid]
        ctx = pair_context(p["unit_id"], p["control_id"])
        models = {}
        for prov, rs in sorted(llm[pid].items()):
            rs = sorted(rs, key=lambda r: r["run"])
            models[prov] = {"model": rs[0]["model"], "runs": rs,
                            "median_alignment": st.median(r["alignment"] for r in rs),
                            "median_realization": st.median(r["realization"] for r in rs)}
        items.append({"pair": pid, "context": ctx,
                      "pcef": {"tuple": p["tuple"], "measures": p["measures"], "effective_weights": p["effective_weights"],
                               "coverage_detail": p["coverage_detail"], "relatedness": p["relatedness"],
                               "directionality_detail": p["directionality_detail"],
                               "realization": run["realization"][p["control_id"]]},
                      "llms": models})
    random.Random(SEED).shuffle(items)
    pack = {"version": "panel-pack v1 (2026-10-05)", "seed": SEED, "source_run": a.run_json,
            "pcef_config": run["provenance"]["config_status"], "items": items}
    raw = json.dumps(pack, indent=2)
    pack["sha256"] = hashlib.sha256(raw.encode()).hexdigest()[:12]
    out = ROOT / a.out; out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(pack, indent=2), encoding="utf-8")
    print(f"{len(items)} unique pairs (from {sum(len(ana['shortlist'][ax]) for ax in ('alignment', 'realization'))} shortlist rows) -> {out}")


if __name__ == "__main__":
    main()
