"""
Accounts for the web app: email + password, server-side sessions in SQLite.

Passwords are stored only as argon2id hashes. The browser holds a random session token in an
HttpOnly cookie; the database keeps only its SHA-256, so a copy of the database cannot be used
to sign in. Failed sign-ins are limited per address and per email.

The database lives at PCEF_DB if set, else <PCEF_DATA_DIR>/pcef.sqlite3, else instance/pcef.sqlite3.
"""

from __future__ import annotations

import hashlib
import os
import re
import secrets
import sqlite3
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[1]
COOKIE = "pcef_session"
SESSION_DAYS = 14
MIN_PASSWORD = 10
MAX_PASSWORD = 256
FAIL_LIMIT = 5                 # failed sign-ins allowed per window ...
FAIL_WINDOW = 15 * 60          # ... of this many seconds
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

_hasher = PasswordHasher()
_DUMMY_HASH = _hasher.hash("pcef-timing-equaliser")
_fails: dict[str, list[float]] = {}
_fail_lock = threading.Lock()

router = APIRouter(prefix="/api/auth")


def db_path() -> Path:
    if os.environ.get("PCEF_DB"):
        return Path(os.environ["PCEF_DB"])
    base = os.environ.get("PCEF_DATA_DIR")
    return (Path(base) if base else ROOT / "instance") / "pcef.sqlite3"


@contextmanager
def connect():
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    try:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_utc TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS sessions (
                token_sha256 TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                expires_utc TEXT NOT NULL);
        """)
        yield con
        con.commit()
    finally:
        con.close()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _sha(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _too_many(keys: list[str]) -> bool:
    cutoff = time.monotonic() - FAIL_WINDOW
    with _fail_lock:
        for k in keys:
            _fails[k] = [t for t in _fails.get(k, []) if t > cutoff]
        return any(len(_fails[k]) >= FAIL_LIMIT for k in keys)


def _record_fail(keys: list[str]) -> None:
    with _fail_lock:
        for k in keys:
            _fails.setdefault(k, []).append(time.monotonic())


def _start_session(con: sqlite3.Connection, user_id: int, request: Request, response: Response) -> None:
    token = secrets.token_urlsafe(32)
    expires = _now() + timedelta(days=SESSION_DAYS)
    con.execute("INSERT INTO sessions VALUES (?, ?, ?)", (_sha(token), user_id, expires.isoformat()))
    con.execute("DELETE FROM sessions WHERE expires_utc < ?", (_now().isoformat(),))
    https = request.url.scheme == "https" or request.headers.get("x-forwarded-proto", "") == "https"
    response.set_cookie(COOKIE, token, max_age=SESSION_DAYS * 86400, httponly=True, samesite="lax",
                        secure=https, path="/")


def current_user(request: Request) -> dict | None:
    token = request.cookies.get(COOKIE)
    if not token:
        return None
    with connect() as con:
        row = con.execute("SELECT u.id, u.email FROM sessions s JOIN users u ON u.id = s.user_id "
                          "WHERE s.token_sha256 = ? AND s.expires_utc > ?", (_sha(token), _now().isoformat())).fetchone()
    return dict(row) if row else None


class Credentials(BaseModel):
    email: str
    password: str


def _clean(c: Credentials) -> tuple[str, str]:
    email = c.email.strip().lower()
    if len(email) > 254 or not EMAIL.match(email):
        raise HTTPException(400, "Enter a valid email address.")
    if len(c.password) > MAX_PASSWORD:
        raise HTTPException(400, f"Use a password of at most {MAX_PASSWORD} characters.")
    return email, c.password


@router.post("/signup")
def signup(c: Credentials, request: Request, response: Response):
    email, password = _clean(c)
    if len(password) < MIN_PASSWORD:
        raise HTTPException(400, f"Use a password of at least {MIN_PASSWORD} characters.")
    with connect() as con:
        try:
            cur = con.execute("INSERT INTO users (email, password_hash, created_utc) VALUES (?, ?, ?)",
                              (email, _hasher.hash(password), _now().isoformat(timespec="seconds")))
        except sqlite3.IntegrityError:
            raise HTTPException(409, "An account with this email already exists. Sign in instead.")
        _start_session(con, cur.lastrowid, request, response)
    return {"email": email}


@router.post("/login")
def login(c: Credentials, request: Request, response: Response):
    email, password = _clean(c)
    keys = [f"ip:{request.client.host if request.client else '-'}", f"email:{email}"]
    if _too_many(keys):
        raise HTTPException(429, "Too many failed attempts. Wait 15 minutes and try again.")
    with connect() as con:
        row = con.execute("SELECT id, password_hash FROM users WHERE email = ?", (email,)).fetchone()
        try:
            _hasher.verify(row["password_hash"] if row else _DUMMY_HASH, password)   # same work either way
            ok = row is not None
        except (VerifyMismatchError, VerificationError):
            ok = False
        if not ok:
            _record_fail(keys)
            raise HTTPException(401, "Email or password is incorrect.")
        if _hasher.check_needs_rehash(row["password_hash"]):
            con.execute("UPDATE users SET password_hash = ? WHERE id = ?", (_hasher.hash(password), row["id"]))
        _start_session(con, row["id"], request, response)
    return {"email": email}


@router.post("/logout")
def logout(request: Request, response: Response):
    token = request.cookies.get(COOKIE)
    if token:
        with connect() as con:
            con.execute("DELETE FROM sessions WHERE token_sha256 = ?", (_sha(token),))
    response.delete_cookie(COOKIE, path="/")
    return {"signed_out": True}


class Confirm(BaseModel):
    password: str


@router.post("/delete")
def delete_account(c: Confirm, request: Request, response: Response):
    """Delete the signed-in account with its sessions and saved runs. Needs the password again."""
    user = current_user(request)
    if not user:
        raise HTTPException(401, "Sign in first.")
    with connect() as con:
        row = con.execute("SELECT password_hash FROM users WHERE id = ?", (user["id"],)).fetchone()
        try:
            _hasher.verify(row["password_hash"], c.password)
        except (VerifyMismatchError, VerificationError):
            raise HTTPException(401, "That password is not correct, so nothing was deleted.")
        con.execute("DELETE FROM users WHERE id = ?", (user["id"],))      # sessions and runs go with it
    response.delete_cookie(COOKIE, path="/")
    return {"deleted": True}


@router.get("/me")
def me(request: Request):
    from .admin import is_admin
    u = current_user(request)
    return {"email": u["email"] if u else None, "admin": is_admin(u)}
