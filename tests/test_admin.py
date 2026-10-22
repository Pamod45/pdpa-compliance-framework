"""Admin role: panel and admin pages for listed admins only; panel stays open when no admins are set."""
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

from app import auth  # noqa: E402
from app.server import app  # noqa: E402

PW = "correct horse battery"


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("PCEF_DB", str(tmp_path / "test.sqlite3"))
    monkeypatch.setattr(auth, "_fails", {})
    with TestClient(app) as c:
        yield c


def sign_up(c, email):
    c.post("/api/auth/logout")
    assert c.post("/api/auth/signup", json={"email": email, "password": PW}).status_code == 200


def test_panel_open_when_no_admins(client, monkeypatch):
    monkeypatch.delenv("PCEF_ADMIN_EMAILS", raising=False)
    assert client.get("/api/meta").json()["panel_restricted"] is False
    assert client.get("/api/panel/progress?expert=E1").status_code == 200


def test_panel_and_admin_pages_for_admins_only(client, monkeypatch):
    monkeypatch.setenv("PCEF_ADMIN_EMAILS", "Owner@Example.com")
    assert client.get("/api/meta").json()["panel_restricted"] is True
    assert client.get("/api/panel/progress?expert=E1").status_code == 403          # signed out
    sign_up(client, "guest@example.com")
    assert client.get("/api/auth/me").json() == {"email": "guest@example.com", "admin": False}
    assert client.get("/api/panel/progress?expert=E1").status_code == 403
    assert client.get("/api/admin/users").status_code == 403
    sign_up(client, "owner@example.com")
    assert client.get("/api/auth/me").json()["admin"] is True
    assert client.get("/api/panel/progress?expert=E1").status_code == 200
    users = client.get("/api/admin/users").json()
    assert users["totals"]["users"] == 2 and {u["email"] for u in users["users"] if u["admin"]} == {"owner@example.com"}


def test_admin_can_remove_a_user_but_not_themself(client, monkeypatch):
    monkeypatch.setenv("PCEF_ADMIN_EMAILS", "owner@example.com")
    sign_up(client, "guest@example.com")
    sign_up(client, "owner@example.com")
    ids = {u["email"]: u["id"] for u in client.get("/api/admin/users").json()["users"]}
    assert client.delete(f"/api/admin/users/{ids['owner@example.com']}").status_code == 400
    assert client.delete(f"/api/admin/users/{ids['guest@example.com']}").status_code == 200
    assert [u["email"] for u in client.get("/api/admin/users").json()["users"]] == ["owner@example.com"]
