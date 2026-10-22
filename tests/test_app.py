"""UI server plumbing with the stand-in embedder (no model download)."""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root, so `app` imports

os.environ["PCEF_EMBEDDER"] = "tfidf"
os.environ["PCEF_WARM_SAMPLE"] = "0"
fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from app.server import PANEL_OUT, app  # noqa: E402


def test_meta_and_run_and_bad_upload():
    with TestClient(app) as c:
        m = c.get("/api/meta").json()
        assert len(m["clauses"]) == 11 and "feature_weights" in m["constants"]
        r = c.post("/api/run", data={"clause_ids": "PDPA-s10", "use_sample": "true"})
        assert r.status_code == 200 and all("context" in p for p in r.json()["pairs"])
        bad = c.post("/api/run", data={"clause_ids": "PDPA-s10"}, files={"ssp": ("x.json", b"{}", "application/json")})
        assert bad.status_code == 400
        assert c.post("/api/run", data={"clause_ids": ""}).status_code in (400, 422)


def as_admin(c, monkeypatch, tmp_path):
    monkeypatch.setenv("PCEF_DB", str(tmp_path / "test.sqlite3"))
    monkeypatch.setenv("PCEF_ADMIN_EMAILS", "owner@example.com")
    assert c.post("/api/auth/signup", json={"email": "owner@example.com", "password": "correct horse battery"}).status_code == 200


def test_panel_rejects_out_of_range(monkeypatch, tmp_path):
    with TestClient(app) as c:
        as_admin(c, monkeypatch, tmp_path)
        r = c.post("/api/panel/response", json={"expert": "T", "pair": "p", "pack_sha256": "x", "blind_alignment": 1.5,
                                                "blind_realization": 0, "confidence": "low",
                                                "defensible_alignment": "pcef", "defensible_realization": "pcef"})
        assert r.status_code == 400
        assert not PANEL_OUT.exists() or "1.5" not in PANEL_OUT.read_text()


def test_upload_size_limit_and_closed_panel(monkeypatch, tmp_path):
    import app.server as srv
    monkeypatch.setattr(srv, "MAX_UPLOAD_BYTES", 10)
    monkeypatch.setattr(srv, "PANEL_WRITES", False)
    with TestClient(app) as c:
        as_admin(c, monkeypatch, tmp_path)
        big = c.post("/api/run", data={"clause_ids": "PDPA-s10"}, files={"ssp": ("x.json", b"{" + b" " * 50 + b"}", "application/json")})
        assert big.status_code == 413
        r = c.post("/api/panel/response", json={"expert": "T", "pair": "p", "pack_sha256": "x", "blind_alignment": 0.5,
                                                "blind_realization": 0.5, "confidence": "low",
                                                "defensible_alignment": "pcef", "defensible_realization": "pcef"})
        assert r.status_code == 403


def test_sample_ssp_download():
    with TestClient(app) as c:
        r = c.get("/api/sample-ssp")
        assert r.status_code == 200 and "system-security-plan" in r.json()
        assert "fleettrack_ssp.json" in r.headers["content-disposition"]


def test_sample_runs_are_cached():
    import app.server as srv
    with TestClient(app) as c:
        first = c.post("/api/run", data={"clause_ids": "PDPA-s23,PDPA-s10", "use_sample": "true"})
        second = c.post("/api/run", data={"clause_ids": "PDPA-s10,PDPA-s23", "use_sample": "true"})
        assert first.status_code == second.status_code == 200
        assert first.content == second.content
        assert ("PDPA-s10", "PDPA-s23") in srv._sample_cache


def test_walkthrough_follows_two_sample_pairs():
    with TestClient(app) as c:
        w = c.get("/api/walkthrough").json()
        assert [k["pair"]["unit_id"] + "|" + k["pair"]["control_id"] for k in w["cases"]] == ["s10-u1|ac-3", "s10-u1|sc-28"]
        assert w["ssp"]["roles"] == ["controller", "processor"]
        assert all(k["role_check_other"]["passed"] is False for k in w["cases"])   # controller duties drop for a processor-only plan
        assert all(k["ssp_entry"]["control-id"] == k["pair"]["control_id"] for k in w["cases"])


def test_meta_serves_the_frozen_constants():
    with TestClient(app) as c:
        k = c.get("/api/meta").json()
    assert len(k["config_sha256"]) == 12
    assert k["constants"]["compatibility"]["technical"]["technical"] == 1.0
    assert k["constants"]["specificity_full_words"] > 0 and k["constants"]["negation_cues"]
