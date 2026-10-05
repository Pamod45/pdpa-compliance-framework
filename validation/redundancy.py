"""
Non-redundancy check: pairwise Pearson |r| among the scoring measures over all scored
pairs. Any |r| > 0.85 is flagged for review (merge or report), not treated as a failure.
A measure with zero variance has no defined correlation, and this is reported.

    python validation/redundancy.py outputs/run_method_of_record/run.json
"""

from __future__ import annotations

import argparse
import json
import math
from itertools import combinations
from pathlib import Path

THRESHOLD = 0.85
MEASURES = ["relatedness", "coverage", "strength", "directionality", "maturity"]


def pearson(xs, ys):
    n = len(xs)
    if n < 3:
        return None, "n < 3"
    mx, my = sum(xs) / n, sum(ys) / n
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs)); sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if sx == 0 or sy == 0:
        return None, "zero variance (" + ("first" if sx == 0 else "second") + " measure is constant)"
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy), ""


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("run_json"); ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    run = json.loads(Path(a.run_json).read_text(encoding="utf-8"))
    rows = []
    for p in run["pairs"]:
        if p["status"] != "scored":
            continue
        m = dict(p["measures"]); m["maturity"] = p["tuple"]["realization"]
        rows.append(m)

    stats = {}
    for k in MEASURES:
        v = [r[k] for r in rows if r[k] is not None]
        stats[k] = {"n": len(v), "min": min(v), "max": max(v), "distinct": len(set(round(x, 6) for x in v))}

    res = []
    for a_, b_ in combinations(MEASURES, 2):
        pair = [(r[a_], r[b_]) for r in rows if r[a_] is not None and r[b_] is not None]
        r_, why = pearson([x for x, _ in pair], [y for _, y in pair])
        res.append({"a": a_, "b": b_, "n": len(pair), "r": None if r_ is None else round(r_, 3),
                    "flag": r_ is not None and abs(r_) > THRESHOLD, "note": why})

    L = ["# Non-redundancy check", "",
         f"- Source: `{a.run_json}` | config {run['provenance']['config_status']}",
         f"- Scored pairs: {len(rows)} | rule: |r| > {THRESHOLD} -> flagged for collapse-or-report review", "",
         "## Measure spread", "", "| Measure | n | min | max | distinct values |", "|---|---|---|---|---|"]
    L += [f"| {k} | {s['n']} | {s['min']:.3f} | {s['max']:.3f} | {s['distinct']} |" for k, s in stats.items()]
    L += ["", "## Pairwise Pearson r", "", "| Pair | n | r | Flag |", "|---|---|---|---|"]
    L += [f"| {x['a']} - {x['b']} | {x['n']} | {'undefined' if x['r'] is None else x['r']} | "
          f"{'**FLAG**' if x['flag'] else ('n/a: ' + x['note'] if x['r'] is None else '')} |" for x in res]
    out = Path(a.out) if a.out else Path(a.run_json).with_name("redundancy.md")
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    out.with_suffix(".json").write_text(json.dumps({"stats": stats, "pairs": res}, indent=2), encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
