"""
Discriminant test harness (criteria in validation/DISCRIMINANT_PROTOCOL*.md).

    python validation/discriminant.py --embedder sbert
    python validation/discriminant.py --embedder sbert --set v2 --config config_v2 --out outputs/discriminant_v2
    python validation/discriminant.py --embedder sbert --set v3 --config config_v3 --out outputs/discriminant_v3

--set selects the variant files and --config the scoring configuration. When the
configuration enables the relevance check, H5 compares strong FleetTrack under that
configuration with the v1.1 baseline. Variant sets from earlier iterations are
reported as secondary results, not as evidence.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pcef.parsers import CatalogIndex, SspDocument, normalize_control
from pcef.pipeline.config import PipelineConfig
from pcef.pipeline.embedder import make_embedder
from pcef.pipeline.measures import maturity, row_text
from pcef.pipeline.run import DEFAULTS, run

ROOT = Path(__file__).resolve().parents[1]
STRONG = ROOT / "data/raw/ssps/fleettrack/fleettrack_ssp.json"
SET_DIRS = {"v1": ROOT / "data/raw/ssps/fleettrack_variants", "v2": ROOT / "data/raw/ssps/fleettrack_variants_v2",
            "v3": ROOT / "data/raw/ssps/fleettrack_variants_v3"}
NAMES = ["partial", "broken", "vague_padded", "swapped"]
TOL = 1e-6
H5_KEEP = 0.80   # H5: strong Realization must keep >= 80% of its v1.1 value


def variants(set_name):
    return {"strong": STRONG, **{n: SET_DIRS[set_name] / f"fleettrack_{n}.json" for n in NAMES}}


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--embedder", choices=["sbert", "tfidf"], default="sbert")
    ap.add_argument("--set", choices=list(SET_DIRS), default="v1")
    ap.add_argument("--config", default=DEFAULTS["config"])
    ap.add_argument("--baseline-config", default=DEFAULTS["config"])
    ap.add_argument("--out", default="outputs/discriminant")
    a = ap.parse_args(argv)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    cfg_dir = str(ROOT / a.config)
    V = variants(a.set)

    res = {}
    for name, ssp in V.items():
        res[name] = run(None, a.embedder, str(out / name), str(ROOT / DEFAULTS["profiles"]),
                        str(ROOT / DEFAULTS["catalog"]), str(ssp), cfg_dir)
        print("ran", name)

    strong_ids = sorted(ir["control-id"] for ir in json.loads(STRONG.read_text(encoding="utf-8"))
                        ["system-security-plan"]["control-implementation"]["implemented-requirements"])
    ix = CatalogIndex.from_file(str(ROOT / DEFAULTS["catalog"]))
    cfg = PipelineConfig.load(cfg_dir)
    base_cfg = PipelineConfig.load(str(ROOT / a.baseline_config))
    # Secondary: earlier variant sets under the same scorer (reported, not evidence)
    all_ssps = {f"{a.set}:{k}": v for k, v in V.items()}
    for other_set in SET_DIRS:
        if other_set != a.set:
            all_ssps.update({f"other-{other_set}:{k}": v for k, v in variants(other_set).items() if k != "strong"})
    ncs = {key: {c: normalize_control(c, ix, SspDocument.from_file(str(p))) for c in strong_ids}
           for key, p in all_ssps.items() if Path(p).exists()}
    reference = {}
    for cid in strong_ids:  # catalog rows of every FleetTrack control (identical across variants)
        rnc = normalize_control(cid, ix)
        reference[cid] = [row_text(rnc, sp) for sp in rnc.sub_parts]
    emb = make_embedder(a.embedder)
    emb.fit([b.description for d in ncs.values() for nc in d.values() for sp in nc.sub_parts for b in sp.by_components]
            + [row_text(nc, sp) for d in ncs.values() for nc in d.values() for sp in nc.sub_parts]
            + [t for rows in reference.values() for t in rows])

    def R(key, c=cfg):
        return {cid: (maturity(nc, c.params, emb, reference).value or 0.0) for cid, nc in ncs[key].items()}

    Rm = {n: R(f"{a.set}:{n}") for n in V}
    mean = {n: sum(Rm[n].values()) / len(strong_ids) for n in V}

    def align(name):
        return {(p["unit_id"], p["control_id"]): p["tuple"]["alignment"] for p in res[name]["pairs"] if p["status"] == "scored"}
    A = {n: align(n) for n in V}
    same_keys = all(set(A[n]) == set(A["strong"]) for n in V)
    max_diff = max((abs(A[n][k] - A["strong"][k]) for n in V for k in A["strong"] if k in A[n]), default=0.0)

    h1 = mean["strong"] > mean["partial"] > mean["broken"]
    viol = [c for c in strong_ids if not (Rm["strong"][c] >= Rm["partial"][c] >= Rm["broken"][c])]
    h2 = same_keys and max_diff <= TOL
    h3 = mean["vague_padded"] <= mean["partial"]
    h4 = mean["swapped"] <= mean["partial"]

    rel_on = bool(cfg.params["maturity"].get("relevance", {}).get("enabled"))
    L = ["# Discriminant test results", "",
         f"- Variant set: {a.set} | Scorer config: {res['strong']['provenance']['config_status']} "
         f"(sha256 {res['strong']['provenance']['config_sha256']['pcef_params'][:12]}) | relevance check: {'ON' if rel_on else 'OFF'}",
         f"- Embedder: {res['strong']['provenance']['embedder']['model_id']} @ {res['strong']['provenance']['embedder']['revision']}",
         f"- Controls compared: {len(strong_ids)} (FleetTrack SSP controls)", "",
         "## Verdicts (criteria fixed in the protocol before scoring)", "",
         "| Hypothesis | Criterion | Result |", "|---|---|---|",
         f"| H1 aligned degradation | strong > partial > broken | **{'PASS' if h1 else 'FAIL'}** ({mean['strong']:.3f} > {mean['partial']:.3f} > {mean['broken']:.3f}) |",
         f"| H2 Alignment independence | identical (<= {TOL}) | **{'PASS' if h2 else 'FAIL'}** (same pairs: {same_keys}, max diff {max_diff:.2e}) |",
         f"| H3 padding resistance | vague_padded <= partial | **{'PASS' if h3 else 'FAIL'}** ({mean['vague_padded']:.3f} vs {mean['partial']:.3f}) |",
         f"| H4 wrong-mechanism detection | swapped <= partial | **{'PASS' if h4 else 'FAIL'}** ({mean['swapped']:.3f} vs {mean['partial']:.3f}) |"]
    extra = {}
    if rel_on:
        base_strong = sum(R(f"{a.set}:strong", base_cfg).values()) / len(strong_ids)
        h5 = mean["strong"] >= H5_KEEP * base_strong
        L.append(f"| H5 genuine text kept | strong(this) >= {H5_KEEP:.0%} of strong(baseline) | **{'PASS' if h5 else 'FAIL'}** "
                 f"({mean['strong']:.3f} vs {H5_KEEP:.0%} x {base_strong:.3f} = {H5_KEEP * base_strong:.3f}) |")
        extra = {"h5": h5, "baseline_strong": base_strong}
    L += ["", f"Per-control order violations for H1 (reported, not pass/fail): {viol or 'none'}", "",
          "## Mean Realization", "", "| Variant | Mean |", "|---|---|"]
    L += [f"| {n} | {mean[n]:.3f} |" for n in V]
    secondary = {k.split(":", 1)[0].replace("other-", "") + ":" + k.split(":", 1)[1]: sum(R(k).values()) / len(strong_ids)
                 for k in ncs if k.startswith("other-")}
    if secondary:
        L += ["", "## SECONDARY (already-seen variant sets, same scorer) - not evidence", "",
              "| Set:variant | Mean |", "|---|---|"] + [f"| {n} | {v:.3f} |" for n, v in sorted(secondary.items())]
    L += ["", "## Realization per control", "", "| Control | " + " | ".join(V) + " |", "|---" * (len(V) + 1) + "|"]
    L += [f"| {c} | " + " | ".join(f"{Rm[n][c]:.3f}" for n in V) + " |" for c in strong_ids]
    (out / "discriminant.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    (out / "discriminant.json").write_text(json.dumps({
        "set": a.set, "config": a.config, "mean": mean, "realization": Rm, "h1": h1, "h1_violations": viol,
        "h2": h2, "h2_max_diff": max_diff, "h3": h3, "h4": h4, **extra, "secondary": secondary}, indent=2), encoding="utf-8")
    print("done ->", out / "discriminant.md")


if __name__ == "__main__":
    main()
