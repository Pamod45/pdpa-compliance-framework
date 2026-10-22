"""Drafting an SSP with an LLM: the model is replaced by a fixed answer, so no key or network is used."""
import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root, so `app` imports

os.environ["PCEF_EMBEDDER"] = "tfidf"
os.environ["PCEF_WARM_SAMPLE"] = "0"
pytest.importorskip("fastapi")
pytest.importorskip("argon2")
from fastapi.testclient import TestClient  # noqa: E402

from app import auth, draft  # noqa: E402
from app.server import app  # noqa: E402

PW = "correct horse battery"
ANSWER = {
    "system_name": "FleetTrack", "pdpa_role": "controller,processor",
    "components": [{"key": "api", "title": "FleetTrack API", "description": "FastAPI backend", "state": "operational"}],
    "controls": [
        {"control_id": "ac-3", "part": "", "component": "api", "description": "require_roles() and require_same_company() in app/rbac.py gate every request.", "remarks": ""},
        {"control_id": "ac-2", "part": "a", "component": "api", "description": "Four account types are defined in app/models.py.", "remarks": ""},
        {"control_id": "sc-28", "part": "z", "component": "db", "description": "Encryption at rest is not implemented; fleettrack.db is unencrypted.", "remarks": "KNOWN GAP"},
        {"control_id": "xx-1", "part": "", "component": "api", "description": "Not a real control.", "remarks": ""},
    ]}


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("PCEF_DB", str(tmp_path / "test.sqlite3"))
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(auth, "_fails", {})
    monkeypatch.setattr(draft, "_calls", {})
    calls = []
    monkeypatch.setattr(draft, "_call_llm", lambda text: calls.append(text) or (json.dumps(ANSWER), "gemini-test-001"))
    with TestClient(app) as c:
        c.calls = calls
        yield c


def test_sample_draft_is_valid_oscal_and_cached(client):
    r = client.post("/api/draft", json={"sample_id": "fleettrack"}).json()
    ssp = r["ssp"]["system-security-plan"]
    ids = [ir["control-id"] for ir in ssp["control-implementation"]["implemented-requirements"]]
    assert ids == ["ac-2", "ac-3", "sc-28"]                                   # xx-1 left out
    assert any("xx-1" in w for w in r["warnings"]) and any("SC-28 has no part 'z'" in w for w in r["warnings"])
    assert ssp["system-characteristics"]["props"] == [{"name": "pdpa-role", "value": "controller,processor"}]
    assert r["cached"] is False and len(client.calls) == 1 and r["provenance"]["model_version"] == "gemini-test-001"
    again = client.post("/api/draft", json={"sample_id": "fleettrack"}).json()
    assert again["cached"] is True and again["ssp"] == r["ssp"] and len(client.calls) == 1   # no second LLM call


def test_draft_scores_with_the_frozen_scorer(client):
    ssp = client.post("/api/draft", json={"sample_id": "fleettrack"}).json()["ssp"]
    res = client.post("/api/run", data={"clause_ids": "PDPA-s10"},
                      files={"ssp": ("draft.json", json.dumps(ssp).encode(), "application/json")}).json()
    assert any(p["control_id"] == "ac-3" and p["status"] == "scored" for p in res["pairs"])


def test_own_text_is_for_admins_only(client, monkeypatch):
    assert client.post("/api/draft", json={"text": "Our system encrypts everything."}).status_code == 403
    monkeypatch.setenv("PCEF_ADMIN_EMAILS", "owner@example.com")
    client.post("/api/auth/signup", json={"email": "owner@example.com", "password": PW})
    r = client.post("/api/draft", json={"text": "Our system uses role checks."})
    assert r.status_code == 200 and r.json()["provenance"]["source"] == "Pasted document"


def test_limits_and_missing_key(client, monkeypatch):
    monkeypatch.setenv("PCEF_LLM_DAILY_LIMIT", "1")
    monkeypatch.setenv("PCEF_ADMIN_EMAILS", "owner@example.com")
    client.post("/api/auth/signup", json={"email": "owner@example.com", "password": PW})
    assert client.post("/api/draft", json={"text": "first"}).status_code == 200
    assert client.post("/api/draft", json={"text": "second"}).status_code == 429
    monkeypatch.delenv("GEMINI_API_KEY")
    assert client.post("/api/draft", json={"sample_id": "fleettrack"}).status_code == 503
    assert client.get("/api/draft/status").json()["configured"] is False
