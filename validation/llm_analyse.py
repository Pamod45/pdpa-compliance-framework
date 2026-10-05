"""
LLM baseline - analysis (see validation/LLM_BASELINE_PROTOCOL.md).

  python validation/llm_analyse.py --calls outputs/llm_chat/calls.jsonl --out outputs/llm_chat
  python validation/llm_analyse.py --calls outputs/llm_chat/calls.jsonl --out outputs/llm_chat --skip-pcef-repeat

Reads the parsed LLM calls and the PCEF method-of-record run.json, and by default re-runs
PCEF 5 times to confirm identical output. Writes llm_analysis.md and .json to --out.
Descriptive only: it does not claim which scorer is right.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics as st
import tempfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AXES = ("alignment", "realization")


def _ranks(xs):
    order = sorted(range(len(xs)), key=lambda i: xs[i]); r = [0.0] * len(xs); i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def spearman(a, b):
    if len(a) < 3:
        return None
    ra, rb = _ranks(a), _ranks(b)
    try:
        return round(st.correlation(ra, rb), 3)
    except st.StatisticsError:
        return None  # a constant series


def pcef_tuples(run_json):
    run = json.loads(Path(run_json).read_text(encoding="utf-8"))
    return {f"{p['unit_id']}|{p['control_id']}": p["tuple"] for p in run["pairs"] if p["status"] == "scored"}


def pcef_repeat(n):
    from pcef.pipeline.run import DEFAULTS, run
    digests = []
    with tempfile.TemporaryDirectory() as td:
        for i in range(n):
            r = run(None, "sbert", f"{td}/r{i}", *(str(ROOT / DEFAULTS[k]) for k in ("profiles", "catalog", "ssp", "config")))
            t = sorted((p["unit_id"], p["control_id"], json.dumps(p.get("tuple"), sort_keys=True)) for p in r["pairs"])
            digests.append(hashlib.sha256(json.dumps(t).encode()).hexdigest())
    return digests


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--calls", default="outputs/llm_baseline/calls.jsonl")
    ap.add_argument("--run-json", default="outputs/run_method_of_record_v1_1/run.json")
    ap.add_argument("--out", default="outputs/llm_baseline")
    ap.add_argument("--pcef-runs", type=int, default=5)
    ap.add_argument("--skip-pcef-repeat", action="store_true")
    a = ap.parse_args(argv)

    pcef = pcef_tuples(ROOT / a.run_json)
    calls = [json.loads(l) for l in (ROOT / a.calls).read_text(encoding="utf-8").splitlines() if l.strip()]
    groups = defaultdict(lambda: defaultdict(list))   # (prov, cond) -> pair -> [parsed|None]
    meta = defaultdict(lambda: {"served": set(), "errors": 0, "temp_rejected": 0, "calls": 0})
    for c in calls:
        k = (c["provider"], c["condition"])
        groups[k][c["pair"]].append(c.get("parsed"))
        m = meta[k]; m["calls"] += 1
        if c.get("served_model"):
            m["served"].add(c["served_model"])
        if not c.get("parsed"):
            m["errors"] += 1
            if "temperature" in (c.get("error") or "").lower():
                m["temp_rejected"] += 1

    rows, medians = [], {}
    for k in sorted(groups):
        pairs = groups[k]
        full = {p: v for p, v in pairs.items() if v and all(x for x in v)}
        ident = sum(1 for v in full.values() if len({(x["alignment"], x["realization"]) for x in v}) == 1)
        sds = {ax: [st.pstdev([x[ax] for x in v]) for v in full.values()] for ax in AXES}
        rng = {ax: max((max(x[ax] for x in v) - min(x[ax] for x in v) for v in full.values()), default=0) for ax in AXES}
        med = {p: {ax: st.median([x[ax] for x in v if x]) for ax in AXES} for p, v in pairs.items() if any(v)}
        medians[k] = med
        common = [p for p in med if p in pcef and pcef[p]["realization"] is not None]
        rho = {ax: spearman([pcef[p][ax] for p in common], [med[p][ax] for p in common]) for ax in AXES}
        m = meta[k]
        rows.append({"provider": k[0], "condition": k[1], "served_models": sorted(m["served"]),
                     "calls": m["calls"], "failed": m["errors"], "temperature_rejected": m["temp_rejected"],
                     "pairs_complete": len(full), "pairs_identical_all_runs": ident,
                     "pct_identical": round(100 * ident / len(full), 1) if full else None,
                     "mean_sd": {ax: round(st.mean(sds[ax]), 4) if sds[ax] else None for ax in AXES},
                     "max_range": {ax: round(rng[ax], 3) for ax in AXES}, "spearman_vs_pcef": rho})

    # disagreement shortlist for the panel: PCEF vs mean of the temp0 medians across providers
    # shortlist reference: temp0 medians if that condition exists (API design), else every condition (chat design)
    t0 = [medians[k] for k in medians if k[1] == "temp0"] or list(medians.values())
    short = {}
    for ax in AXES:
        diffs = []
        for p, tup in pcef.items():
            vals = [m[p][ax] for m in t0 if p in m]
            if vals and tup.get(ax) is not None:
                diffs.append((abs(tup[ax] - st.mean(vals)), p, tup[ax], st.mean(vals)))
        short[ax] = [{"pair": p, "pcef": round(x, 3), "llm_mean": round(y, 3), "abs_diff": round(d, 3)}
                     for d, p, x, y in sorted(diffs, reverse=True)[:8]]

    # C1 construct separation: Realization is a CONTROL property, so the same control (same SSP text) in the
    # same run should get the same Realization whichever clause it is paired with.
    within = {}
    for (prov, cond), pairs in groups.items():
        by = defaultdict(list)
        for pair, v in pairs.items():
            for i, x in enumerate(v):
                if x:
                    by[(i, pair.split("|")[1])].append(x["realization"])
        multi = {k: v for k, v in by.items() if len(v) > 1}
        bad = {f"run{k[0] + 1}:{k[1]}": v for k, v in multi.items() if len(set(v)) > 1}
        within[f"{prov}/{cond}"] = {"groups": len(multi), "inconsistent": len(bad), "examples": dict(list(bad.items())[:3])}
    # LLM-to-LLM agreement (Spearman of medians), to compare with each LLM's agreement with PCEF
    inter = []
    keys = sorted(medians)
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            common = sorted(set(medians[keys[i]]) & set(medians[keys[j]]))
            inter.append({"a": "/".join(keys[i]), "b": "/".join(keys[j]),
                          **{ax: spearman([medians[keys[i]][p][ax] for p in common],
                                          [medians[keys[j]][p][ax] for p in common]) for ax in AXES}})

    pcef_digests = None if a.skip_pcef_repeat else pcef_repeat(a.pcef_runs)

    L = ["# LLM baseline analysis (descriptive - the LLMs are a contrast case, not an oracle)", ""]
    if pcef_digests:
        same = len(set(pcef_digests)) == 1
        L += [f"**R1 PCEF reproducibility:** {a.pcef_runs} runs -> {'IDENTICAL' if same else 'DIFFERENT'} "
              f"(digest {pcef_digests[0][:12]}{'' if same else ' ...'})", ""]
    L += ["## R2 LLM run-to-run variance", "",
          "| Provider | Condition | Served model(s) | Calls | Failed | Temp rejected | Pairs complete | Identical across runs | Mean SD align | Mean SD real | Max range align | Max range real |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        L.append(f"| {r['provider']} | {r['condition']} | {', '.join(r['served_models']) or '-'} | {r['calls']} | {r['failed']} | "
                 f"{r['temperature_rejected']} | {r['pairs_complete']} | {r['pairs_identical_all_runs']} ({r['pct_identical']}%) | "
                 f"{r['mean_sd']['alignment']} | {r['mean_sd']['realization']} | {r['max_range']['alignment']} | {r['max_range']['realization']} |")
    L += ["", "## T1 Triangulation: Spearman rank correlation with PCEF (medians of runs; no threshold)", "",
          "| Provider | Condition | rho Alignment | rho Realization |", "|---|---|---|---|"]
    L += [f"| {r['provider']} | {r['condition']} | {r['spearman_vs_pcef']['alignment']} | {r['spearman_vs_pcef']['realization']} |" for r in rows]
    L += ["", "## C1 Construct separation: same control, same run, different clause -> same Realization?", "",
          "PCEF: identical by design (Realization never reads the clause).", "",
          "| Provider/condition | run x control groups | inconsistent | examples |", "|---|---|---|---|"]
    L += [f"| {k} | {v['groups']} | {v['inconsistent']} | {v['examples']} |" for k, v in within.items()]
    L += ["", "## LLM-to-LLM agreement (Spearman of medians) - compare with each LLM vs PCEF above", "",
          "| A | B | rho Alignment | rho Realization |", "|---|---|---|---|"]
    L += [f"| {x['a']} | {x['b']} | {x['alignment']} | {x['realization']} |" for x in inter]
    for ax in AXES:
        L += ["", f"## Panel shortlist - largest {ax} disagreements (PCEF vs mean of LLM medians)", "",
              "| Pair | PCEF | LLM mean | abs diff |", "|---|---|---|---|"]
        L += [f"| {d['pair']} | {d['pcef']} | {d['llm_mean']} | {d['abs_diff']} |" for d in short[ax]]
    out = ROOT / a.out; out.mkdir(parents=True, exist_ok=True)
    (out / "llm_analysis.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    (out / "llm_analysis.json").write_text(json.dumps({"pcef_digests": pcef_digests, "rows": rows, "shortlist": short,
                                                                  "construct_separation": within, "llm_to_llm": inter}, indent=2), encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
