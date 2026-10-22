"""
Saved runs for signed-in users.

A run is saved by the server when it is scored, never uploaded by the browser, so a saved result is
always one the frozen scorer produced. The full result is stored compressed, next to a short summary
(the same headline the overview shows) so the list loads without opening every result.
"""

from __future__ import annotations

import json
import zlib
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from .auth import connect, current_user

GUIDE = 0.5                                   # reading guide used by the overview, not a pass mark
NON_DUTY = {"trigger", "exemption", "reclassification"}
MAX_RUNS = 50                                 # per user
MAX_NAME = 120

router = APIRouter(prefix="/api/runs")

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    ssp_name TEXT NOT NULL,
    clause_ids TEXT NOT NULL,
    created_utc TEXT NOT NULL,
    config_status TEXT NOT NULL,
    embedder TEXT NOT NULL,
    summary TEXT NOT NULL,
    result BLOB NOT NULL);
CREATE INDEX IF NOT EXISTS runs_by_user ON runs(user_id, created_utc);
"""


def _table(con) -> None:
    con.executescript(SCHEMA)


def summarise(res: dict) -> dict:
    """The overview headline: duties covered and built, and the two averages at each duty's best control."""
    by_unit: dict[str, list[dict]] = {}
    for p in res["pairs"]:
        by_unit.setdefault(p["unit_id"], []).append(p)
    duties = built = 0
    a_sum = r_sum = 0.0
    judged = 0
    for u in res["units"]:
        if u["unit_type"] in NON_DUTY:
            continue
        duties += 1
        scored = sorted((p for p in by_unit.get(u["unit_id"], []) if p["status"] == "scored"),
                        key=lambda p: p["tuple"]["alignment"], reverse=True)
        if not scored:
            continue
        best = scored[0]["tuple"]
        judged += 1
        a_sum += best["alignment"]
        r_sum += best["realization"] or 0.0
        if u["scored"] and best["alignment"] >= GUIDE and (best["realization"] or 0.0) >= GUIDE:
            built += 1
    return {"duties": duties, "built": built, "judged": judged,
            "avg_alignment": round(a_sum / judged, 4) if judged else None,
            "avg_realization": round(r_sum / judged, 4) if judged else None,
            "pairs_scored": sum(p["status"] == "scored" for p in res["pairs"])}


def save(user: dict, body: bytes, clause_ids: list[str]) -> bytes:
    """Store a result for this user and return it with a `saved_run` note added."""
    res = json.loads(body)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    name = f"{res['ssp_name']} - {len(clause_ids)} clause{'s' if len(clause_ids) != 1 else ''}"
    with connect() as con:
        _table(con)
        (count,) = con.execute("SELECT COUNT(*) FROM runs WHERE user_id = ?", (user["id"],)).fetchone()
        if count >= MAX_RUNS:
            res["saved_run"] = {"id": None, "note": f"Not saved: you already have {MAX_RUNS} saved runs. Delete some to save new ones."}
            return json.dumps(res).encode()
        cur = con.execute(
            "INSERT INTO runs (user_id, name, ssp_name, clause_ids, created_utc, config_status, embedder, summary, result) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (user["id"], name, res["ssp_name"], ",".join(clause_ids), now, res["provenance"]["config_status"],
             res["provenance"]["embedder"]["model_id"], json.dumps(summarise(res)), zlib.compress(body, 6)))
    res["saved_run"] = {"id": cur.lastrowid, "name": name}
    return json.dumps(res).encode()


def _owner(request: Request) -> dict:
    user = current_user(request)
    if not user:
        raise HTTPException(401, "Sign in to see your saved runs.")
    return user


@router.get("")
def list_runs(request: Request):
    user = _owner(request)
    with connect() as con:
        _table(con)
        rows = con.execute("SELECT id, name, ssp_name, clause_ids, created_utc, config_status, embedder, summary "
                           "FROM runs WHERE user_id = ? ORDER BY created_utc DESC, id DESC", (user["id"],)).fetchall()
    return {"limit": MAX_RUNS, "runs": [{**dict(r), "clause_ids": r["clause_ids"].split(","),
                                         "summary": json.loads(r["summary"])} for r in rows]}


@router.get("/{run_id}")
def get_run(run_id: int, request: Request):
    user = _owner(request)
    with connect() as con:
        _table(con)
        row = con.execute("SELECT name, result FROM runs WHERE id = ? AND user_id = ?", (run_id, user["id"])).fetchone()
    if not row:
        raise HTTPException(404, "That saved run was not found.")
    res = json.loads(zlib.decompress(row["result"]))
    res["saved_run"] = {"id": run_id, "name": row["name"]}
    return Response(json.dumps(res).encode(), media_type="application/json")


class Rename(BaseModel):
    name: str


@router.patch("/{run_id}")
def rename_run(run_id: int, body: Rename, request: Request):
    user = _owner(request)
    name = body.name.strip()
    if not name or len(name) > MAX_NAME:
        raise HTTPException(400, f"Use a name of 1 to {MAX_NAME} characters.")
    with connect() as con:
        _table(con)
        cur = con.execute("UPDATE runs SET name = ? WHERE id = ? AND user_id = ?", (name, run_id, user["id"]))
    if cur.rowcount == 0:
        raise HTTPException(404, "That saved run was not found.")
    return {"id": run_id, "name": name}


@router.delete("/{run_id}")
def delete_run(run_id: int, request: Request):
    user = _owner(request)
    with connect() as con:
        _table(con)
        cur = con.execute("DELETE FROM runs WHERE id = ? AND user_id = ?", (run_id, user["id"]))
    if cur.rowcount == 0:
        raise HTTPException(404, "That saved run was not found.")
    return {"deleted": run_id}
