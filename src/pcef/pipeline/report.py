"""Stage 7: clause-level and control-level markdown report generated from run.json."""

from __future__ import annotations

from pathlib import Path


def _f(x) -> str:
    return "-" if x is None else f"{x:.3f}"


def write_markdown(res: dict, path: Path) -> None:
    pv = res["provenance"]
    L = ["# PCEF run report", ""]
    if pv["standin_warning"]:
        L += [f"> **{pv['standin_warning']}**", ""]
    L += [f"- Run at (UTC): {pv['run_at_utc']}",
          f"- Embedder: {pv['embedder']['model_id']} @ {pv['embedder']['revision']}",
          f"- Clauses: {', '.join(res['scope']['clauses'])} | SSP: {res['scope']['ssp_system']}",
          f"- System PDPA role(s): {pv['system_roles']['roles'] or 'not declared'} ({pv['system_roles']['source']})",
          f"- Unit text mode: {pv['unit_text_mode']} | Floor gate: {'ON' if pv['relatedness_floor_enabled'] else 'OFF (sensitivity run - NOT method of record)'}",
          f"- Thresholds: floor={pv['thresholds_used']['relatedness_floor']} | Coverage: "
          + (f"ramp {pv['coverage_ramp'][0]}-{pv['coverage_ramp'][1]}" if pv['coverage_mode'] == 'ramp'
             else f"threshold {pv['thresholds_used']['coverage_threshold']} (sensitivity run)"),
          f"- Rules: {'; '.join(pv['rules'])}",
          f"- Config status: {pv['config_status']}", ""]

    L += ["## Clause level (one row per unit x control pair)", "",
          "| Clause | Unit | Control | Source | Status | Rel | Cov | Str | Dir | Alignment | Realization |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for p in sorted(res["pairs"], key=lambda r: (r["unit_id"], -(r.get("tuple", {}).get("alignment") or -1))):
        m = p.get("measures", {})
        t = p.get("tuple", {})
        status = p["status"] if p["status"] == "scored" else f"excluded ({p['excluded_by']})"
        L.append(f"| {p['clause_id']} | {p['unit_id']} | {p['control_id']} | {p['pair_source']} | {status} | "
                 f"{_f(p['relatedness']['value'])} | {_f(m.get('coverage'))} | {_f(m.get('strength'))} | "
                 f"{_f(m.get('directionality'))} | {_f(t.get('alignment'))} | {_f(t.get('realization'))} |")

    s3 = res["stage3"]
    if s3["unanchored_units"] or s3["not_scored_units"] or s3["dropped_hints"]:
        L += ["", f"- Unanchored units (no control hint): {s3['unanchored_units'] or 'none'}",
              f"- Not-scored units: {s3['not_scored_units'] or 'none'}",
              f"- Dropped hints: {s3['dropped_hints'] or 'none'}"]

    flags = sorted({f for p in res["pairs"] for f in p["gates"]["applicability"]["flags"]})
    if flags:
        L += ["", "Applicability flags raised:"] + [f"- {f}" for f in flags]

    L += ["", "## Control level (Realization is a control property)", "",
          "| Control | Realization | Rows counted | Row statuses |", "|---|---|---|---|"]
    for cid, r in sorted(res["realization"].items()):
        sts = {}
        for row in r["rows"].values():
            sts[row["status"]] = sts.get(row["status"], 0) + 1
        L.append(f"| {cid} | {_f(r['value'])} | {r['counted_rows']} | "
                 f"{', '.join(f'{k}:{v}' for k, v in sorted(sts.items()))} |")
    path.write_text("\n".join(L) + "\n", encoding="utf-8")
