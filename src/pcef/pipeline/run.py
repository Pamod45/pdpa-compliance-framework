"""
End-to-end runner for stages 3-7, using the stage 1-2 profiles, catalog and SSP.

    python -m pcef.pipeline.run --clauses PDPA-s10 PDPA-s23 --embedder sbert --out outputs/run_s10_s23
    python -m pcef.pipeline.run --all --embedder sbert --out outputs/run_full

Writes <out>/run.json (full results with provenance) and <out>/report.md (summary tables).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

from ..models import PDPAProfileSet
from ..parsers import CatalogIndex, SspDocument, normalize_control, NormalizationReport
from .aggregate import alignment, tuple_view
from .config import PipelineConfig
from .embedder import make_embedder
from .gates import ROLE_PROP, GateResult, applicability_gate, parse_roles, relatedness_floor_gate
from .measures import (coverage, directionality, maturity, relatedness, row_text,
                       strength_match, unit_text)
from .pairing import generate_pairs
from .report import write_markdown

DEFAULTS = {
    "profiles": "data/symbolized/pdpa_clause_profiles.json",
    "catalog": "data/raw/catalogs/nist_sp800_53_rev5/NIST_SP-800-53_rev5_catalog.json",
    "ssp": "data/raw/ssps/fleettrack/fleettrack_ssp.json",
    "config": "config",
}


def _sha256(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _version(pkg: str) -> str:
    try:
        return metadata.version(pkg)
    except metadata.PackageNotFoundError:
        return "not installed"


def _system_props(ssp_path: str) -> dict[str, str]:
    raw = json.loads(Path(ssp_path).read_text(encoding="utf-8"))
    props = raw["system-security-plan"]["system-characteristics"].get("props", [])
    return {p["name"]: p["value"] for p in props}


def run(clause_ids: list[str] | None, embedder_kind: str, out_dir: str,
        profiles: str, catalog_path: str, ssp_path: str, config_dir: str,
        model_id: str | None = None, revision: str | None = None,
        system_role: str | None = None, emb=None) -> dict:
    """Run the pipeline. `emb` lets a caller reuse an already-loaded embedder."""
    cfg = PipelineConfig.load(config_dir)
    prof = PDPAProfileSet.from_json_file(profiles)
    clauses = [c for c in prof.clauses if clause_ids is None or c.clause_id in clause_ids]
    missing = set(clause_ids or []) - {c.clause_id for c in clauses}
    if missing:
        raise SystemExit(f"unknown clause ids: {sorted(missing)}")

    ix = CatalogIndex.from_file(catalog_path)
    ssp = SspDocument.from_file(ssp_path)
    sys_props = _system_props(ssp_path)
    if system_role:
        roles, role_source = parse_roles(system_role), "--system-role"
    elif sys_props.get(ROLE_PROP):
        roles, role_source = parse_roles(sys_props[ROLE_PROP]), f"SSP prop '{ROLE_PROP}'"
    else:
        roles, role_source = None, "not declared"

    # Stage 3: candidate pairs
    pairing = generate_pairs(clauses, ix, ssp)

    # Normalise only the controls that were paired
    norm_report = NormalizationReport()
    controls = {cid: normalize_control(cid, ix, ssp, norm_report)
                for cid in sorted({p.control_id for p in pairing.pairs})}

    # Fit the embedder on every text it will compare
    if emb is None:
        emb = make_embedder(embedder_kind, model_id, revision)
    if cfg.params["relatedness_rollup"]["value"] != "max":
        raise ValueError("only relatedness_rollup = 'max' is implemented")
    text_mode = cfg.params["unit_text_mode"]["value"]
    floor_on = bool(cfg.params["relatedness_floor_enabled"]["value"])
    corpus = [unit_text(p.unit, text_mode) for p in pairing.pairs]
    corpus += [a.name for p in pairing.pairs for a in p.unit.attributes]
    corpus += [row_text(nc, sp) for nc in controls.values() for sp in nc.sub_parts]
    corpus += [b.description for nc in controls.values() for sp in nc.sub_parts for b in sp.by_components]
    # Reference rows for relative relevance: catalog rows of every control the SSP lists
    reference = {}
    for sc_ in ssp:
        if sc_.control_id in ix:
            ref_nc = normalize_control(sc_.control_id, ix)
            reference[sc_.control_id] = [row_text(ref_nc, sp) for sp in ref_nc.sub_parts]
    corpus += [t for rows in reference.values() for t in rows]
    emb.fit(corpus)

    floor = cfg.per_embedder("relatedness_floor", emb.name)
    cov_thr = cfg.per_embedder("coverage_threshold", emb.name)
    cov_mode = cfg.params["coverage_mode"]["value"]
    cov_ramp = tuple(cfg.params["coverage_ramp"][emb.name])

    # Realization is a control property, so it is computed once per control
    realization = {cid: maturity(nc, cfg.params, emb, reference) for cid, nc in controls.items()}

    pair_rows = []
    for p in pairing.pairs:
        nc = controls[p.control_id]
        row = {"clause_id": p.clause.clause_id, "unit_id": p.unit.unit_id,
               "control_id": p.control_id, "control_title": nc.title,
               "pair_source": p.source}

        # Stage 4: gates
        app = applicability_gate(p.unit, roles, role_source)
        rel = relatedness(emb, p.unit, nc, text_mode)
        flo = (relatedness_floor_gate(rel.value, floor) if floor_on
               else GateResult(True, "floor gate DISABLED (sensitivity run, not method of record)"))
        row["gates"] = {"applicability": vars(app), "relatedness_floor": vars(flo)}
        row["relatedness"] = {"value": round(rel.value, 4), **rel.detail}
        if not (app.passed and flo.passed):
            row["status"] = "excluded"
            row["excluded_by"] = "applicability" if not app.passed else "relatedness_floor"
            pair_rows.append(row)
            continue

        # Stage 5: alignment measures
        cov = coverage(emb, p.unit, nc, cov_thr, cov_mode, cov_ramp)
        stm = strength_match(p.unit, nc, cfg.params)
        drc = directionality(p.clause, nc, cfg.directionality)
        measures = {"relatedness": rel.value, "coverage": cov.value,
                    "strength": stm.value, "directionality": drc.value}
        a, eff_w = alignment(measures, cfg.params["alignment_weights"])

        # Stages 5-6: realization and the (A, R) tuple
        r = realization[p.control_id].value
        row.update({
            "status": "scored",
            "measures": {k: (None if v is None else round(v, 4)) for k, v in measures.items()},
            "effective_weights": eff_w,
            "coverage_detail": cov.detail, "strength_detail": stm.detail,
            "directionality_detail": drc.detail,
            "tuple": tuple_view(a, r),
        })
        pair_rows.append(row)

    result = {
        "provenance": {
            "run_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "argv": sys.argv,
            "python": platform.python_version(), "platform": platform.platform(),
            "packages": {k: _version(k) for k in
                         ("pcef", "pydantic", "sentence-transformers", "torch", "transformers")},
            "embedder": {"kind": emb.name, "model_id": emb.model_id, "revision": emb.revision},
            "standin_warning": (emb.name == "tfidf") and
                "TF-IDF STAND-IN: numbers are plumbing checks only, not results.",
            "inputs_sha256": {"profiles": _sha256(profiles), "catalog": _sha256(catalog_path),
                              "ssp": _sha256(ssp_path)},
            "config_sha256": {"pcef_params": cfg.params_sha256,
                              "directionality_table": cfg.directionality_sha256},
            "system_roles": {"roles": sorted(roles) if roles else None, "source": role_source},
            "thresholds_used": {"relatedness_floor": floor, "coverage_threshold": cov_thr},
            "relatedness_floor_enabled": floor_on,
            "coverage_mode": cov_mode, "coverage_ramp": list(cov_ramp),
            "unit_text_mode": text_mode,
            "rules": ["relatedness row roll-up = max", "maturity horizontal = max",
                      "maturity vertical = mean (na excluded, absent = 0)"],
            "config_status": (cfg.params["_status"].split(" - ")[0] if str(cfg.params.get("_status", "")).startswith("FROZEN")
                              and str(cfg.directionality.get("_status", "")).startswith("FROZEN")
                              else "DRAFT - values not yet frozen"),
        },
        "scope": {"clauses": [c.clause_id for c in clauses], "ssp_system": ssp.system_name},
        "stage3": {"pairs": len(pairing.pairs), "unanchored_units": pairing.unanchored_units,
                   "not_scored_units": pairing.not_scored_units,
                   "dropped_hints": pairing.dropped_hints},
        "stage2_report": {"ambiguous_na": norm_report.ambiguous_na,
                          "unknown_control_ids": norm_report.unknown_control_ids},
        "realization": {cid: {"value": None if m.value is None else round(m.value, 4), **m.detail}
                        for cid, m in realization.items()},
        "pairs": pair_rows,
    }

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "run.json").write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    write_markdown(result, out / "report.md")
    return result


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="PCEF Stages 3-7")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--clauses", nargs="+", help="e.g. PDPA-s10 PDPA-s23")
    g.add_argument("--all", action="store_true", help="every clause in the profile set")
    ap.add_argument("--embedder", choices=["sbert", "tfidf"], default="sbert")
    ap.add_argument("--model", default=None, help="override the SBERT model id")
    ap.add_argument("--revision", default=None, help="pin an exact model commit hash")
    ap.add_argument("--system-role", default=None,
                    help="PDPA role(s) of the system, comma-separated, e.g. processor or processor,controller")
    ap.add_argument("--out", required=True)
    for k, v in DEFAULTS.items():
        ap.add_argument(f"--{k}", default=v)
    a = ap.parse_args(argv)
    res = run(None if a.all else a.clauses, a.embedder, a.out, a.profiles, a.catalog,
              a.ssp, a.config, a.model, a.revision, a.system_role)
    n_scored = sum(1 for p in res["pairs"] if p["status"] == "scored")
    print(f"done: {len(res['pairs'])} pairs ({n_scored} scored) -> {a.out}")


if __name__ == "__main__":
    main()
