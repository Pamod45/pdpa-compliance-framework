"""
Admin role: site owners named in PCEF_ADMIN_EMAILS (comma-separated).

When admins are configured, the expert panel and the admin pages are open to them only. When none
are configured (a local run), the panel stays open as before so the evaluation workflow still works.
Create the admin account yourself before adding its email here: whoever registers an address first owns it.
"""

from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException, Request

from .auth import connect, current_user
from .history import ensure_table

router = APIRouter(prefix="/api/admin")


def admin_emails() -> set[str]:
    return {e.strip().lower() for e in os.environ.get("PCEF_ADMIN_EMAILS", "").split(",") if e.strip()}


def is_admin(user: dict | None) -> bool:
    return bool(user) and user["email"] in admin_emails()


def panel_restricted() -> bool:
    return bool(admin_emails())


def require_panel_access(request: Request) -> None:
    if panel_restricted() and not is_admin(current_user(request)):
        raise HTTPException(403, "The expert panel is open to site admins only.")


def require_admin(request: Request) -> dict:
    user = current_user(request)
    if not is_admin(user):
        raise HTTPException(403, "Admins only.")
    return user


@router.get("/users")
def users(request: Request):
    require_admin(request)
    with connect() as con:
        ensure_table(con)
        rows = con.execute("""
            SELECT u.id, u.email, u.created_utc,
                   (SELECT COUNT(*) FROM runs r WHERE r.user_id = u.id) AS runs,
                   (SELECT COALESCE(SUM(LENGTH(r.result)), 0) FROM runs r WHERE r.user_id = u.id) AS stored_bytes,
                   (SELECT MAX(r.created_utc) FROM runs r WHERE r.user_id = u.id) AS last_run_utc
            FROM users u ORDER BY u.created_utc DESC""").fetchall()
    admins = admin_emails()
    return {"users": [{**dict(r), "admin": r["email"] in admins} for r in rows],
            "totals": {"users": len(rows), "runs": sum(r["runs"] for r in rows),
                       "stored_bytes": sum(r["stored_bytes"] for r in rows)}}


@router.delete("/users/{user_id}")
def delete_user(user_id: int, request: Request):
    me = require_admin(request)
    if user_id == me["id"]:
        raise HTTPException(400, "Use your own account page to delete your account.")
    with connect() as con:
        cur = con.execute("DELETE FROM users WHERE id = ?", (user_id,))     # sessions and runs go with it
    if cur.rowcount == 0:
        raise HTTPException(404, "That user was not found.")
    return {"deleted": user_id}
