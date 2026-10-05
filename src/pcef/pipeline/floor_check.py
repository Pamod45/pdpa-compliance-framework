"""
Relatedness floor calibration check. Reports only; scores nothing.

Pairs every scored unit with a fixed set of unrelated controls and compares their
Relatedness with the real Stage 3 pairs, using the same roll-up (best catalog row)
as the pipeline. It shows where the configured floor sits between the two
distributions; it does not choose the floor.

    python -m pcef.pipeline.floor_check --all --embedder sbert --out outputs/floor_check
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..models import PDPAProfileSet
from ..parsers import CatalogIndex, SspDocument, normalize_control
from .config import PipelineConfig
from .embedder import make_embedder
from .measures import relatedness, row_text, unit_text
from .pairing import generate_pairs
from .run import DEFAULTS


def _q(xs: list[float], q: float) -> float:
    s = sorted(xs)
    if not s:
        return float("nan")
    i = (len(s) - 1) * q
    lo, hi = int(i), min(int(i) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (i - lo)


def _summary(xs: list[float]) -> dict:
    return {"n": len(xs), "min": round(min(xs), 4), "p25": round(_q(xs, .25), 4),
            "median": round(_q(xs, .5), 4), "p75": round(_q(xs, .75), 4), "max": round(max(xs), 4)}


def check(clause_ids, embedder_kind, out_dir, profiles, catalog_path, ssp_path, config_dir,
          model_id=None, revision=None) -> dict:
    cfg = PipelineConfig.load(config_dir)
    negs = json.loads((Path(config_dir) / "floor_check_negatives.json").read_text(encoding="utf-8"))
    prof = PDPAProfileSet.from_json_file(profiles)
    clauses = [c for c in prof.clauses if clause_ids is None or c.clause_id in clause_ids]
    ix, ssp = CatalogIndex.from_file(catalog_path), SspDocument.from_file(ssp_path)

    pairing = generate_pairs(clauses, ix, ssp)
    real_ids = sorted({p.control_id for p in pairing.pairs})
    neg_ids = [c for c in negs["controls"] if c in ix]
    controls = {cid: normalize_control(cid, ix, ssp) for cid in set(real_ids) | set(neg_ids)}
    units = list({p.unit.unit_id: p.unit for p in pairing.pairs}.values())

    mode = cfg.params["unit_text_mode"]["value"]
    emb = make_embedder(embedder_kind, model_id, revision)
    emb.fit([unit_text(u, mode) for u in units] +
            [row_text(nc, sp) for nc in controls.values() for sp in nc.sub_parts])
    floor = cfg.per_embedder("relatedness_floor", emb.name)

    real = [{"unit": p.unit.unit_id, "control": p.control_id,
             "rel": relatedness(emb, p.unit, controls[p.control_id], mode).value} for p in pairing.pairs]
    neg = [{"unit": u.unit_id, "control": c, "rel": relatedness(emb, u, controls[c], mode).value}
           for u in units for c in neg_ids]

    per_unit = []
    for u in units:
        r = [x["rel"] for x in real if x["unit"] == u.unit_id]
        n = [x["rel"] for x in neg if x["unit"] == u.unit_id]
        per_unit.append({"unit": u.unit_id, "lowest_real": round(min(r), 4),
                         "highest_negative": round(max(n), 4),
                         "margin": round(min(r) - max(n), 4)})

    res = {
        "embedder": {"model_id": emb.model_id, "revision": emb.revision},
        "floor_in_config": floor, "negative_controls": neg_ids,
        "real_pairs": _summary([x["rel"] for x in real]),
        "negative_pairs": _summary([x["rel"] for x in neg]),
        "negatives_at_or_above_floor": sum(x["rel"] >= floor for x in neg),
        "real_below_floor": sum(x["rel"] < floor for x in real),
        "per_unit": sorted(per_unit, key=lambda d: d["margin"]),
        "top_negatives": sorted(({**x, "rel": round(x["rel"], 4)} for x in neg),
                                key=lambda d: -d["rel"])[:10],
    }
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    (out / "floor_check.json").write_text(json.dumps(res, indent=2), encoding="utf-8")

    L = ["# Relatedness floor check", "",
         f"- Embedder: {emb.model_id} @ {emb.revision}",
         f"- Floor in config: {floor}", f"- Negative controls: {', '.join(neg_ids)}", "",
         "| Set | n | min | p25 | median | p75 | max |", "|---|---|---|---|---|---|---|"]
    for name, k in (("Real pairs", "real_pairs"), ("Unrelated pairs", "negative_pairs")):
        s = res[k]
        L.append(f"| {name} | {s['n']} | {s['min']} | {s['p25']} | {s['median']} | {s['p75']} | {s['max']} |")
    L += ["", f"- Unrelated pairs at/above floor (would wrongly pass): "
              f"{res['negatives_at_or_above_floor']} of {res['negative_pairs']['n']}",
          f"- Real pairs below floor (would wrongly be excluded): "
          f"{res['real_below_floor']} of {res['real_pairs']['n']}", "",
          "## Per unit (sorted by margin; negative margin = an unrelated control beat a real one)", "",
          "| Unit | Lowest real | Highest unrelated | Margin |", "|---|---|---|---|"]
    L += [f"| {d['unit']} | {d['lowest_real']} | {d['highest_negative']} | {d['margin']} |"
          for d in res["per_unit"]]
    L += ["", "## Ten highest unrelated pairs", "", "| Unit | Control | Rel |", "|---|---|---|"]
    L += [f"| {d['unit']} | {d['control']} | {d['rel']} |" for d in res["top_negatives"]]
    (out / "floor_check.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    return res


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Relatedness floor calibration check")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--clauses", nargs="+"); g.add_argument("--all", action="store_true")
    ap.add_argument("--embedder", choices=["sbert", "tfidf"], default="sbert")
    ap.add_argument("--model", default=None); ap.add_argument("--revision", default=None)
    ap.add_argument("--out", required=True)
    for k, v in DEFAULTS.items():
        ap.add_argument(f"--{k}", default=v)
    a = ap.parse_args(argv)
    r = check(None if a.all else a.clauses, a.embedder, a.out, a.profiles, a.catalog, a.ssp,
              a.config, a.model, a.revision)
    print(f"done: {r['real_pairs']['n']} real, {r['negative_pairs']['n']} unrelated -> {a.out}")


if __name__ == "__main__":
    main()
