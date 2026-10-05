"""
Pipeline tests for stages 3-7. They use the TF-IDF stand-in so no model download is
needed, and check structure and invariants rather than score values.
"""

import json
from pathlib import Path

import pytest

from pcef.pipeline.aggregate import alignment
from pcef.pipeline.run import DEFAULTS, run

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def result(tmp_path_factory):
    out = tmp_path_factory.mktemp("run")
    return run(["PDPA-s10", "PDPA-s23"], "tfidf", str(out),
               *(str(ROOT / DEFAULTS[k]) for k in ("profiles", "catalog", "ssp", "config"))), out


def test_outputs_written(result):
    _, out = result
    assert (out / "run.json").exists() and (out / "report.md").exists()
    json.loads((out / "run.json").read_text(encoding="utf-8"))


def test_expected_pairs(result):
    res, _ = result
    got = {(p["unit_id"], p["control_id"]) for p in res["pairs"]}
    assert got == {("s10-u1", c) for c in ("sc-8", "sc-13", "sc-28", "ac-2", "ac-3")} | \
                  {("s23-u1", c) for c in ("ir-6", "ir-8", "ir-8.1")}


def test_scored_pairs_carry_a_tuple_in_range(result):
    res, _ = result
    for p in res["pairs"]:
        if p["status"] == "scored":
            t = p["tuple"]
            assert 0.0 <= t["alignment"] <= 1.0
            assert t["realization"] is None or 0.0 <= t["realization"] <= 1.0
        else:
            assert "tuple" not in p  # excluded pairs are not scored low, they are not scored


def test_control_absent_from_ssp_has_zero_realization(result):
    res, _ = result
    assert res["realization"]["sc-13"]["value"] == 0.0


def test_standin_is_labelled(result):
    res, _ = result
    assert res["provenance"]["standin_warning"]


def test_alignment_renormalises_when_a_measure_is_missing():
    w = {"coverage": 0.35, "relatedness": 0.25, "directionality": 0.25, "strength": 0.15}
    a, eff = alignment({"coverage": 1.0, "relatedness": 1.0, "directionality": 1.0, "strength": None}, w)
    assert a == pytest.approx(1.0) and "strength" not in eff
    assert sum(eff.values()) == pytest.approx(1.0)


# ---- gates, measures and configuration ---------------------------------------

def _run(tmp_path, **kw):
    return run(["PDPA-s22", "PDPA-s8"], "tfidf", str(tmp_path),
               *(str(ROOT / DEFAULTS[k]) for k in ("profiles", "catalog", "ssp", "config")), **kw)


def test_gate_never_excludes_on_an_undeclared_role():
    from pcef.models import PDPAProfileSet
    from pcef.pipeline.gates import applicability_gate
    prof = PDPAProfileSet.from_json_file(str(ROOT / DEFAULTS["profiles"]))
    unit = next(u for c in prof.clauses for u in c.obligation_units if u.unit_id == "s22-u1")
    g = applicability_gate(unit, None, "not declared")
    assert g.passed
    assert any(f.startswith("actor_unverified") for f in g.flags)


def test_declared_role_is_enforced(tmp_path):
    res = _run(tmp_path, system_role="processor")
    by_unit = {p["unit_id"]: p["gates"]["applicability"]["passed"] for p in res["pairs"]}
    assert by_unit["s22-u1"] is True and by_unit["s8-u1"] is False
    assert res["provenance"]["system_roles"]["source"] == "--system-role"


def test_both_roles_admit_both_actors(tmp_path):
    res = _run(tmp_path, system_role="processor,controller")
    assert all(p["gates"]["applicability"]["passed"] for p in res["pairs"])


def test_control_override_beats_family():
    from pcef.parsers import CatalogIndex, normalize_control
    from pcef.pipeline.config import PipelineConfig
    from pcef.pipeline.measures import control_orientation
    ix = CatalogIndex.from_file(str(ROOT / DEFAULTS["catalog"]))
    table = PipelineConfig.load(str(ROOT / DEFAULTS["config"])).directionality
    assert control_orientation(normalize_control("si-18", ix), table) == ("data_governance", "control_override")
    assert control_orientation(normalize_control("si-12.1", ix), table) == ("data_governance", "base_control_override")
    assert control_orientation(normalize_control("si-4", ix), table) == ("technical", "family")


def test_floor_check_runs(tmp_path):
    from pcef.pipeline.floor_check import check
    r = check(["PDPA-s10"], "tfidf", str(tmp_path),
              *(str(ROOT / DEFAULTS[k]) for k in ("profiles", "catalog", "ssp", "config")))
    assert r["negative_pairs"]["n"] == len(r["negative_controls"]) * len(r["per_unit"])
    assert (tmp_path / "floor_check.md").exists()


def test_relatedness_diagnostic_runs(tmp_path):
    from pcef.pipeline.diagnose_relatedness import diagnose
    args = [str(ROOT / DEFAULTS[k]) for k in ("profiles", "catalog", "ssp", "config")]
    r = diagnose(["PDPA-s10", "PDPA-s23"], "tfidf", str(tmp_path), *args)
    assert r["variants"]["qa_model"] == {"skipped": "needs --embedder sbert"}
    assert "meets_bar" in r["variants"]["baseline"]
    c = diagnose(["PDPA-s10"], "tfidf", str(tmp_path), *args, confirm="baseline")
    assert c["negative_controls"] == ["pe-9", "pe-10", "pe-12", "ma-3", "ma-4"]


def test_leaf_rows_carry_their_parent_stem():
    from pcef.parsers import CatalogIndex, normalize_control
    from pcef.pipeline.measures import row_text
    ix = CatalogIndex.from_file(str(ROOT / DEFAULTS["catalog"]))
    nc = normalize_control("ra-8", ix)
    row = next(sp for sp in nc.sub_parts if sp.smt_id == "ra-8_smt.b.1")
    text = row_text(nc, row)
    assert "Conduct privacy impact assessments" in text and "Initiating a new collection" in text
    assert [sp.smt_id for sp in nc.sub_parts] == ["ra-8_smt.a", "ra-8_smt.b.1", "ra-8_smt.b.2"]  # rows unchanged


def test_method_of_record_settings_are_recorded(result):
    res, _ = result
    pv = res["provenance"]
    assert pv["unit_text_mode"] == "keywords" and pv["relatedness_floor_enabled"] is True


def test_floor_gate_can_be_disabled(tmp_path):
    import shutil
    cfg = tmp_path / "cfg"; shutil.copytree(ROOT / "config", cfg)
    p = json.loads((cfg / "pcef_params.json").read_text(encoding="utf-8"))
    p["relatedness_floor_enabled"]["value"] = False
    (cfg / "pcef_params.json").write_text(json.dumps(p), encoding="utf-8")
    res = run(["PDPA-s10"], "tfidf", str(tmp_path / "o"),
              *(str(ROOT / DEFAULTS[k]) for k in ("profiles", "catalog", "ssp")), str(cfg))
    assert res["provenance"]["relatedness_floor_enabled"] is False
    assert all(p["excluded_by"] != "relatedness_floor" for p in res["pairs"] if p["status"] == "excluded")
    assert "OFF" in (tmp_path / "o" / "report.md").read_text(encoding="utf-8")


def test_declared_gap_is_capped(result):
    res, _ = result
    sc28 = res["realization"]["sc-28"]
    bc = sc28["rows"]["sc-28_smt"]["by_components"][0]
    assert bc["capped"] and bc["uncapped"] > 0.2 and sc28["value"] == 0.2


def test_will_be_no_longer_counts_as_a_gap():
    from pcef.models import ByComponent
    from pcef.pipeline.config import PipelineConfig
    from pcef.pipeline.measures import _by_component_score
    mp = PipelineConfig.load(str(ROOT / DEFAULTS["config"])).params["maturity"]
    b = ByComponent(component_uuid="x", component_status="operational",
                    description="Expired telemetry rows will be purged after 90 days by purge_expired_telemetry in trips.py.")
    _, d = _by_component_score(b, mp)
    assert d["negation_hits"] == [] and not d["capped"]


def test_coverage_ramp_scores_partially_and_is_method_of_record(result):
    res, _ = result
    assert res["provenance"]["coverage_mode"] == "ramp"
    for p in res["pairs"]:
        if p["status"] == "scored" and p["coverage_detail"].get("attributes"):
            d = p["coverage_detail"]
            lo, hi = d["ramp"]
            for a in d["attributes"].values():
                exp = min(max((a["best"] - lo) / (hi - lo), 0.0), 1.0)
                assert a["score"] == pytest.approx(exp, abs=1e-3)


def test_coverage_ramp_arithmetic():
    lo, hi, best = 0.25, 0.45, 0.344
    assert (best - lo) / (hi - lo) == pytest.approx(0.47)


def test_config_is_frozen_and_directionality_symmetric(result):
    from pcef.pipeline.config import PipelineConfig
    res, _ = result
    assert res["provenance"]["config_status"].startswith("FROZEN")
    c = PipelineConfig.load(str(ROOT / DEFAULTS["config"])).directionality["compatibility"]
    for a in c:
        for b in c:
            assert c[a][b] == c[b][a], f"asymmetric cell {a}->{b}"


def test_zero_weight_measure_is_reported_but_ignored(result):
    res, _ = result
    for p in res["pairs"]:
        if p["status"] == "scored":
            assert "strength" not in p["effective_weights"]
            assert sum(p["effective_weights"].values()) == pytest.approx(1.0, abs=1e-3)
