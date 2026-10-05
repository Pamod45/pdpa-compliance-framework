"""Structure-only checks on the degraded variants. These never compute scores."""

import json
import subprocess
import sys
from pathlib import Path

from pcef.models import PDPAProfileSet
from pcef.parsers import CatalogIndex, SspDocument
from pcef.pipeline.pairing import generate_pairs

ROOT = Path(__file__).resolve().parents[1]
VAR = ROOT / "data/raw/ssps/fleettrack_variants"


def _gen():
    subprocess.run([sys.executable, str(ROOT / "validation/degrade_ssp.py")], check=True, capture_output=True)


def test_variants_parse_and_keep_pairing_identical():
    _gen()
    ix = CatalogIndex.from_file(str(ROOT / "data/raw/catalogs/nist_sp800_53_rev5/NIST_SP-800-53_rev5_catalog.json"))
    prof = PDPAProfileSet.from_json_file(str(ROOT / "data/symbolized/pdpa_clause_profiles.json"))
    def pairs(p):
        return {(x.unit.unit_id, x.control_id) for x in generate_pairs(prof.clauses, ix, SspDocument.from_file(str(p))).pairs}
    base = pairs(ROOT / "data/raw/ssps/fleettrack/fleettrack_ssp.json")
    for f in sorted(VAR.glob("*.json")):
        assert pairs(f) == base, f.name


def test_generation_is_deterministic():
    _gen(); first = {f.name: f.read_bytes() for f in VAR.glob("*.json")}
    _gen(); assert first == {f.name: f.read_bytes() for f in VAR.glob("*.json")}


def test_swapped_moves_every_real_text_to_another_control():
    _gen()
    def bcs(p):
        s = json.loads(Path(p).read_text(encoding="utf-8"))["system-security-plan"]
        return {(ir["control-id"], bc["uuid"]): bc["description"]
                for ir in s["control-implementation"]["implemented-requirements"]
                for st in ir.get("statements", []) for bc in st.get("by-components", [])}
    strong, sw = bcs(ROOT / "data/raw/ssps/fleettrack/fleettrack_ssp.json"), bcs(VAR / "fleettrack_swapped.json")
    for (cid, u), text in sw.items():
        if "not implemented" in text.lower():
            assert text == strong[(cid, u)]           # gap texts stay put
        else:
            assert all(text != t for (c, _), t in strong.items() if c == cid)


def test_discriminant_harness_runs_end_to_end(tmp_path):
    """Plumbing only: checks the harness completes and writes its report. Scores are not asserted."""
    _gen()
    r = subprocess.run([sys.executable, str(ROOT / "validation/discriminant.py"), "--embedder", "tfidf",
                        "--out", str(tmp_path)], capture_output=True, text=True, cwd=str(ROOT))
    assert r.returncode == 0, r.stderr[-2000:]
    assert (tmp_path / "discriminant.md").exists()


def test_v2_variants_parse_keep_pairing_and_differ_from_v1():
    subprocess.run([sys.executable, str(ROOT / "validation/degrade_ssp.py"), "--set", "v2"], check=True, capture_output=True)
    _gen()
    v2 = ROOT / "data/raw/ssps/fleettrack_variants_v2"
    for n in ("partial", "broken", "vague_padded", "swapped"):
        assert (v2 / f"fleettrack_{n}.json").read_bytes() != (VAR / f"fleettrack_{n}.json").read_bytes()


def test_v2_harness_runs_end_to_end(tmp_path):
    """Plumbing only (stand-in embedder). Scores are not asserted or read."""
    subprocess.run([sys.executable, str(ROOT / "validation/degrade_ssp.py"), "--set", "v2"], check=True, capture_output=True)
    _gen()
    r = subprocess.run([sys.executable, str(ROOT / "validation/discriminant.py"), "--embedder", "tfidf", "--set", "v2",
                        "--config", "config_v2", "--out", str(tmp_path)], capture_output=True, text=True, cwd=str(ROOT))
    assert r.returncode == 0, r.stderr[-2000:]
    assert "H5" in (tmp_path / "discriminant.md").read_text(encoding="utf-8")


def test_v1_config_has_relevance_off_v2_on():
    from pcef.pipeline.config import PipelineConfig
    assert not PipelineConfig.load(str(ROOT / "config")).params["maturity"].get("relevance", {}).get("enabled")
    assert PipelineConfig.load(str(ROOT / "config_v2")).params["maturity"]["relevance"]["enabled"]


def test_v3_harness_runs_and_relative_mode_is_used(tmp_path):
    """Plumbing only (stand-in embedder). Scores are not asserted or read."""
    for s in ("v1", "v2", "v3"):
        subprocess.run([sys.executable, str(ROOT / "validation/degrade_ssp.py"), "--set", s], check=True, capture_output=True)
    r = subprocess.run([sys.executable, str(ROOT / "validation/discriminant.py"), "--embedder", "tfidf", "--set", "v3",
                        "--config", "config_v3", "--out", str(tmp_path)], capture_output=True, text=True, cwd=str(ROOT))
    assert r.returncode == 0, r.stderr[-2000:]
    strong = json.loads((tmp_path / "strong" / "run.json").read_text(encoding="utf-8"))
    bcs = [b for c in strong["realization"].values() for row in c["rows"].values() for b in row.get("by_components", [])]
    assert bcs and all(b.get("relevance_mode") == "relative" for b in bcs)


def test_relative_relevance_skips_with_too_few_controls(tmp_path):
    """The NIST example lists one control -> relative check must switch off and flag, not crash."""
    from pcef.pipeline.run import DEFAULTS, run
    res = run(None, "tfidf", str(tmp_path), str(ROOT / DEFAULTS["profiles"]), str(ROOT / DEFAULTS["catalog"]),
              str(ROOT / "data/raw/ssps/public/nist_example/enterprise_logging_auditing_ssp.json"), str(ROOT / "config_v3"))
    assert res["provenance"]["config_status"].startswith("FROZEN v3.0")
