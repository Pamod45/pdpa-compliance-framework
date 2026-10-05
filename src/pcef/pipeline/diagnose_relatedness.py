"""
Relatedness diagnostic: compares candidate Relatedness variants against a fixed bar.

The bar, set before any variant was run:
  1. every unit's margin > 0 (each real control scores above every unrelated one)
  2. fewer than 20% of unrelated pairs clear the tightest safe floor

Variants use different score scales, so criterion 2 uses the tightest safe floor
(the lowest real-pair score) rather than the configured 0.20, which is reported
alongside for the raw variants.

Usage: run without --confirm on the primary negative set to choose a variant, then
run --confirm NAME once on the held-out set to check the chosen variant.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..models import PDPAProfileSet
from ..parsers import CatalogIndex, SspDocument, normalize_control
from .embedder import make_embedder
from .measures import row_text, unit_text
from .pairing import generate_pairs
from .run import DEFAULTS

ALT_MODEL = "sentence-transformers/multi-qa-mpnet-base-cos-v1"
BAR_PASS_RATE = 0.20

# name: (model, text_mode, rollup, hub)
VARIANTS = {
    "baseline":         ("default", "plain",    "max",  False),
    "richer_text":      ("default", "keywords", "max",  False),
    "top2_rollup":      ("default", "plain",    "top2", False),
    "hub_correction":   ("default", "plain",    "max",  True),
    "qa_model":         ("alt",     "plain",    "max",  False),
    "text+rollup+hub":  ("default", "keywords", "top2", True),
}


def _unit_text(u, mode: str) -> str:
    return unit_text(u, mode)   # same text builder as the pipeline


def _rollup(xs: list[float], mode: str) -> float:
    s = sorted(xs, reverse=True)
    return s[0] if mode == "max" or len(s) == 1 else (s[0] + s[1]) / 2


def _score_matrix(emb, units, controls, mode, rollup):
    """unit_id -> control_id -> rolled-up cosine."""
    m = {}
    for u in units:
        ut = _unit_text(u, mode)
        m[u.unit_id] = {cid: _rollup([emb.similarity(ut, row_text(nc, sp)) for sp in nc.sub_parts], rollup)
                        for cid, nc in controls.items()}
    return m


def _hub_correct(m, control_ids):
    units = list(m)
    mean = {c: sum(m[u][c] for u in units) / len(units) for c in control_ids}
    return {u: {c: m[u][c] - mean[c] for c in control_ids} for u in units}, mean


def _evaluate(m, real_pairs, neg_ids, floor_cfg, raw_scale: bool) -> dict:
    real = [(u, c, m[u][c]) for u, c in real_pairs]
    neg = [(u, c, m[u][c]) for u in {u for u, _ in real_pairs} for c in neg_ids]
    tight = min(s for *_, s in real)
    per_unit = []
    for u in sorted({u for u, _ in real_pairs}):
        lo = min(s for uu, _, s in real if uu == u)
        hi_c, hi = max(((c, s) for uu, c, s in neg if uu == u), key=lambda t: t[1])
        per_unit.append({"unit": u, "margin": round(lo - hi, 4), "top_unrelated": hi_c})
    pass_tight = sum(s >= tight for *_, s in neg) / len(neg)
    out = {
        "worst_margin": min(d["margin"] for d in per_unit),
        "units_negative_margin": sum(d["margin"] <= 0 for d in per_unit),
        "units": len(per_unit),
        "tightest_safe_floor": round(tight, 4),
        "unrelated_pass_rate_at_tightest_floor": round(pass_tight, 4),
        "unrelated_pass_rate_at_config_floor": (round(sum(s >= floor_cfg for *_, s in neg) / len(neg), 4)
                                                if raw_scale else None),
        "median_real": round(sorted(s for *_, s in real)[len(real) // 2], 4),
        "median_unrelated": round(sorted(s for *_, s in neg)[len(neg) // 2], 4),
        "per_unit": per_unit,
    }
    out["meets_bar"] = out["units_negative_margin"] == 0 and pass_tight < BAR_PASS_RATE
    return out


def diagnose(clause_ids, embedder_kind, out_dir, profiles, catalog_path, ssp_path, config_dir,
             confirm: str | None = None) -> dict:
    negs = json.loads((Path(config_dir) / "floor_check_negatives.json").read_text(encoding="utf-8"))
    params = json.loads((Path(config_dir) / "pcef_params.json").read_text(encoding="utf-8"))
    floor_cfg = float(params["relatedness_floor"][embedder_kind])

    if confirm:
        if confirm not in VARIANTS:
            raise SystemExit(f"unknown variant {confirm!r}; choose from {list(VARIANTS)}")
        variants, neg_key = {confirm: VARIANTS[confirm]}, "holdout_controls"
    else:
        variants, neg_key = VARIANTS, "controls"

    prof = PDPAProfileSet.from_json_file(profiles)
    clauses = [c for c in prof.clauses if clause_ids is None or c.clause_id in clause_ids]
    ix, ssp = CatalogIndex.from_file(catalog_path), SspDocument.from_file(ssp_path)
    pairing = generate_pairs(clauses, ix, ssp)
    neg_ids = [c for c in negs[neg_key] if c in ix]
    real_pairs = sorted({(p.unit.unit_id, p.control_id) for p in pairing.pairs})
    units = list({p.unit.unit_id: p.unit for p in pairing.pairs}.values())
    controls = {cid: normalize_control(cid, ix, ssp)
                for cid in {c for _, c in real_pairs} | set(neg_ids)}

    embedders, results, provenance = {}, {}, {}
    for name, (model, mode, rollup, hub) in variants.items():
        if model == "alt" and embedder_kind != "sbert":
            results[name] = {"skipped": "needs --embedder sbert"}
            continue
        key = (model, embedder_kind)
        if key not in embedders:
            embedders[key] = make_embedder(embedder_kind, ALT_MODEL if model == "alt" else None)
            e = embedders[key]
            e.fit([_unit_text(u, m) for u in units for m in ("plain", "keywords")] +
                  [row_text(nc, sp) for nc in controls.values() for sp in nc.sub_parts])
            provenance[e.model_id] = e.revision
        m = _score_matrix(embedders[key], units, controls, mode, rollup)
        if hub:
            m, _ = _hub_correct(m, list(controls))
        results[name] = _evaluate(m, real_pairs, neg_ids, floor_cfg, raw_scale=not hub)

    res = {"mode": f"CONFIRM on held-out set: {confirm}" if confirm else "primary set (choose here)",
           "bar": {"all_margins_positive": True, "unrelated_pass_rate_below": BAR_PASS_RATE},
           "negative_controls": neg_ids, "models": provenance,
           "real_pairs": len(real_pairs), "variants": results}

    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    stem = f"confirm_{confirm}" if confirm else "diagnostic"
    (out / f"{stem}.json").write_text(json.dumps(res, indent=2), encoding="utf-8")

    L = [f"# Relatedness diagnostic - {res['mode']}", "",
         f"- Negative controls: {', '.join(neg_ids)}",
         f"- Models: {', '.join(f'{k} @ {v}' for k, v in provenance.items())}",
         f"- Bar: every unit margin > 0 AND unrelated pass rate at tightest safe floor < {BAR_PASS_RATE:.0%}", "",
         "| Variant | Meets bar | Units with margin <= 0 | Worst margin | Unrelated pass @ tightest floor "
         "| Tightest floor | Pass @ config floor | Median real | Median unrelated |",
         "|---|---|---|---|---|---|---|---|---|"]
    for name, r in results.items():
        if "skipped" in r:
            L.append(f"| {name} | skipped ({r['skipped']}) | | | | | | | |"); continue
        cfgp = "-" if r["unrelated_pass_rate_at_config_floor"] is None else f"{r['unrelated_pass_rate_at_config_floor']:.0%}"
        L.append(f"| {name} | {'YES' if r['meets_bar'] else 'no'} | {r['units_negative_margin']}/{r['units']} | "
                 f"{r['worst_margin']} | {r['unrelated_pass_rate_at_tightest_floor']:.0%} | {r['tightest_safe_floor']} | "
                 f"{cfgp} | {r['median_real']} | {r['median_unrelated']} |")
    scored = {n: r for n, r in results.items() if "skipped" not in r}
    L += ["", "## Margin per unit (negative = an unrelated control beat a real one)", "",
          "| Unit | " + " | ".join(scored) + " |", "|---" * (len(scored) + 1) + "|"]
    for i, d in enumerate(next(iter(scored.values()))["per_unit"]):
        L.append(f"| {d['unit']} | " + " | ".join(f"{r['per_unit'][i]['margin']}" for r in scored.values()) + " |")
    (out / f"{stem}.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    return res


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Relatedness fix diagnostic")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--clauses", nargs="+"); g.add_argument("--all", action="store_true")
    ap.add_argument("--embedder", choices=["sbert", "tfidf"], default="sbert")
    ap.add_argument("--confirm", default=None, metavar="VARIANT",
                    help="run one chosen variant on the held-out negatives")
    ap.add_argument("--out", required=True)
    for k, v in DEFAULTS.items():
        ap.add_argument(f"--{k}", default=v)
    a = ap.parse_args(argv)
    r = diagnose(None if a.all else a.clauses, a.embedder, a.out, a.profiles, a.catalog, a.ssp,
                 a.config, a.confirm)
    print("done:", ", ".join(f"{n}={'YES' if v.get('meets_bar') else 'no'}" for n, v in r["variants"].items()
                              if "skipped" not in v), "->", a.out)


if __name__ == "__main__":
    main()
