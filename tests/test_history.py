"""Saved runs: saved only when signed in, private to their owner, renamed and deleted by the owner."""
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

from app import auth, history  # noqa: E402
from app.server import app  # noqa: E402

PW = "correct horse battery"
RUN = {"clause_ids": "PDPA-s10", "use_sample": "true"}


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("PCEF_DB", str(tmp_path / "test.sqlite3"))
    monkeypatch.setattr(auth, "_fails", {})
    with TestClient(app) as c:
        yield c


def sign_up(c, email="ana@example.com"):
    assert c.post("/api/auth/signup", json={"email": email, "password": PW}).status_code == 200


def test_runs_are_saved_only_when_signed_in(client):
    assert "saved_run" not in client.post("/api/run", data=RUN).json()
    assert client.get("/api/runs").status_code == 401
    sign_up(client)
    res = client.post("/api/run", data=RUN).json()
    rid = res["saved_run"]["id"]
    listed = client.get("/api/runs").json()["runs"]
    assert [r["id"] for r in listed] == [rid]
    assert listed[0]["clause_ids"] == ["PDPA-s10"] and listed[0]["summary"]["duties"] >= 1
    again = client.get(f"/api/runs/{rid}").json()
    assert again["pairs"] == res["pairs"] and again["saved_run"]["id"] == rid


def test_summary_matches_overview_rule(client):
    sign_up(client)
    res = client.post("/api/run", data=RUN).json()
    s = history.summarise(res)
    assert s["built"] <= s["judged"] <= s["duties"]
    assert s["pairs_scored"] == sum(p["status"] == "scored" for p in res["pairs"])


def test_rename_delete_and_privacy(client):
    sign_up(client)
    rid = client.post("/api/run", data=RUN).json()["saved_run"]["id"]
    assert client.patch(f"/api/runs/{rid}", json={"name": "Before fixes"}).json()["name"] == "Before fixes"
    assert client.patch(f"/api/runs/{rid}", json={"name": "  "}).status_code == 400
    client.post("/api/auth/logout")
    sign_up(client, "ben@example.com")
    assert client.get(f"/api/runs/{rid}").status_code == 404           # another user's run is invisible
    assert client.delete(f"/api/runs/{rid}").status_code == 404
    client.post("/api/auth/logout")
    client.post("/api/auth/login", json={"email": "ana@example.com", "password": PW})
    assert client.delete(f"/api/runs/{rid}").status_code == 200
    assert client.get("/api/runs").json()["runs"] == []


def test_run_limit(client, monkeypatch):
    monkeypatch.setattr(history, "MAX_RUNS", 1)
    sign_up(client)
    assert client.post("/api/run", data=RUN).json()["saved_run"]["id"]
    second = client.post("/api/run", data=RUN).json()["saved_run"]
    assert second["id"] is None and "Delete some" in second["note"]


def test_compare_two_runs(client):
    sign_up(client)
    before = client.post("/api/run", data=RUN).json()["saved_run"]["id"]
    variant = Path(__file__).resolve().parents[1] / "data/raw/ssps/fleettrack_variants/fleettrack_partial.json"
    with variant.open("rb") as fh:
        after = client.post("/api/run", data={"clause_ids": "PDPA-s10"},
                            files={"ssp": ("partial.json", fh, "application/json")}).json()["saved_run"]["id"]
    c = client.get(f"/api/runs/compare?a={after}&b={before}").json()
    assert c["before"]["id"] == before and c["after"]["id"] == after       # oldest first, whatever the order asked
    assert c["same_scorer"] and c["same_clauses"]
    assert c["unchanged"] + sum(r["changed"] for r in c["pairs"]) == len(c["pairs"])
    assert any(r["changed"] for r in c["pairs"])                           # the partial plan scores differently
    assert client.get(f"/api/runs/compare?a={before}&b={before}").status_code == 400


def test_same_plan_twice_has_no_changes(client):
    sign_up(client)
    a = client.post("/api/run", data=RUN).json()["saved_run"]["id"]
    b = client.post("/api/run", data=RUN).json()["saved_run"]["id"]
    c = client.get(f"/api/runs/compare?a={a}&b={b}").json()
    assert c["duties"] == [] and c["unchanged"] == len(c["pairs"])
    assert c["summary"]["before"] == c["summary"]["after"]
