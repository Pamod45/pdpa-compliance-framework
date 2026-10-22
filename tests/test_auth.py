"""Accounts: sign up, sign in, sessions, password storage and the failed sign-in limit."""
import os
import sqlite3
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


def test_signup_signs_in_and_logout_signs_out(client):
    r = client.post("/api/auth/signup", json={"email": " Ana@Example.com ", "password": PW})
    assert r.status_code == 200 and r.json() == {"email": "ana@example.com"}
    assert client.get("/api/auth/me").json()["email"] == "ana@example.com"
    client.post("/api/auth/logout")
    assert client.get("/api/auth/me").json()["email"] is None


def test_login_and_wrong_password(client):
    client.post("/api/auth/signup", json={"email": "ana@example.com", "password": PW})
    client.post("/api/auth/logout")
    assert client.post("/api/auth/login", json={"email": "ana@example.com", "password": "wrong password!"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": "nobody@example.com", "password": PW}).status_code == 401
    assert client.post("/api/auth/login", json={"email": "ANA@example.com", "password": PW}).status_code == 200
    assert client.get("/api/auth/me").json()["email"] == "ana@example.com"


def test_signup_rules(client):
    assert client.post("/api/auth/signup", json={"email": "not-an-email", "password": PW}).status_code == 400
    assert client.post("/api/auth/signup", json={"email": "ana@example.com", "password": "short"}).status_code == 400
    assert client.post("/api/auth/signup", json={"email": "ana@example.com", "password": PW}).status_code == 200
    assert client.post("/api/auth/signup", json={"email": "ana@example.com", "password": PW}).status_code == 409


def test_only_hashes_are_stored(client):
    client.post("/api/auth/signup", json={"email": "ana@example.com", "password": PW})
    token = client.cookies.get(auth.COOKIE)
    con = sqlite3.connect(os.environ["PCEF_DB"])
    pw_hash = con.execute("SELECT password_hash FROM users").fetchone()[0]
    stored = con.execute("SELECT token_sha256 FROM sessions").fetchone()[0]
    con.close()
    assert pw_hash.startswith("$argon2id$") and PW not in pw_hash
    assert token and stored != token and len(stored) == 64


def test_failed_sign_ins_are_limited(client):
    client.post("/api/auth/signup", json={"email": "ana@example.com", "password": PW})
    client.post("/api/auth/logout")
    for _ in range(auth.FAIL_LIMIT):
        assert client.post("/api/auth/login", json={"email": "ana@example.com", "password": "wrong password!"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": "ana@example.com", "password": PW}).status_code == 429


def test_session_cookie_is_httponly(client):
    r = client.post("/api/auth/signup", json={"email": "ana@example.com", "password": PW})
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie
