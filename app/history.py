"""
Saved runs for signed-in users.

A run is saved by the server when it is scored, never uploaded by the browser, so a saved result is
always one the frozen scorer produced. The full result is stored compressed, next to a short summary
(the same headline the overview shows) so the list loads without opening every result.
"""

from __future__ import annotations

import json
import os
import zlib
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from .auth import connect, current_user, db_path

GUIDE = 0.5                                   # reading guide used by the overview, not a pass mark
NON_DUTY = {"trigger", "exemption", "reclassification"}
MAX_RUNS = 50                                 # per user
MAX_NAME = 120


def retention_days() -> int:
    """Saved runs older than this are deleted; 0 keeps them until the user deletes them."""
    return int(os.environ.get("PCEF_RETENTION_DAYS", "365"))


def purge_expired() -> int:
    days = retention_days()
    if days <= 0 or not db_path().exists():
        return 0
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat(timespec="seconds")
    with connect() as con:
        ensure_table(con)
        return con.execute("DELETE FROM runs WHERE created_utc < ?", (cutoff,)).rowcount

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


def ensure_table(con) -> None:
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


def duty_status(res: dict) -> dict[str, dict]:
    """Each duty's reading-guide group and best-fitting control, as the overview sorts them."""
    by_unit: dict[str, list[dict]] = {}
    for p in res["pairs"]:
        by_unit.setdefault(p["unit_id"], []).append(p)
    out = {}
    for u in res["units"]:
        if u["unit_type"] in NON_DUTY:
            continue
        ps = by_unit.get(u["unit_id"], [])
        scored = sorted((p for p in ps if p["status"] == "scored"), key=lambda p: p["tuple"]["alignment"], reverse=True)
        if not u["scored"]:
            status = "notscored"
        elif not ps:
            status = "none"
        elif not scored:
            status = "excluded"
        else:
            t = scored[0]["tuple"]
            status = "weak" if t["alignment"] < GUIDE else "built" if (t["realization"] or 0) >= GUIDE else "paper"
        out[u["unit_id"]] = {"status": status, "clause_id": u["clause_id"], "obligation": u["obligation"],
                             "best": scored[0]["control_id"] if scored else None}
    return out


def compare(before: dict, after: dict) -> dict:
    """Pair-by-pair and duty-by-duty differences between two results."""
    def pairs(res):
        return {(p["unit_id"], p["control_id"]): p for p in res["pairs"]}
    pb, pa = pairs(before), pairs(after)
    rows = []
    for k in sorted(set(pb) | set(pa)):
        b, a = pb.get(k), pa.get(k)
        tb = b["tuple"] if b and b["status"] == "scored" else None
        ta = a["tuple"] if a and a["status"] == "scored" else None
        r3 = lambda x: None if x is None else round(x, 3)     # differences below 0.001 are not shown as changes
        row = {"unit_id": k[0], "control_id": k[1], "title": (a or b)["control_title"],
               "before": {"status": b["status"] if b else "absent", "alignment": tb and r3(tb["alignment"]), "realization": tb and r3(tb["realization"])},
               "after": {"status": a["status"] if a else "absent", "alignment": ta and r3(ta["alignment"]), "realization": ta and r3(ta["realization"])}}
        if tb and ta:
            row["d_alignment"] = round(row["after"]["alignment"] - row["before"]["alignment"], 3)
            row["d_realization"] = round((row["after"]["realization"] or 0) - (row["before"]["realization"] or 0), 3)
        row["changed"] = row["before"] != row["after"]
        rows.append(row)
    rows.sort(key=lambda r: (not r["changed"], -abs(r.get("d_realization") or 0), -abs(r.get("d_alignment") or 0)))
    db, da = duty_status(before), duty_status(after)
    duties = [{"unit_id": u, **da.get(u, db.get(u)), "before": db.get(u, {}).get("status"), "after": da.get(u, {}).get("status")}
              for u in sorted(set(db) | set(da)) if db.get(u, {}).get("status") != da.get(u, {}).get("status")]
    for d in duties:
        d.pop("status", None)
    prov = lambda r: (r["provenance"]["config_status"], r["provenance"]["embedder"]["model_id"], r["provenance"]["embedder"].get("revision"))
    return {"summary": {"before": summarise(before), "after": summarise(after)},
            "same_scorer": prov(before) == prov(after),
            "same_clauses": sorted({u["clause_id"] for u in before["units"]}) == sorted({u["clause_id"] for u in after["units"]}),
            "duties": duties, "pairs": rows, "unchanged": sum(not r["changed"] for r in rows)}


def save(user: dict, body: bytes, clause_ids: list[str]) -> bytes:
    """Store a result for this user and return it with a `saved_run` note added."""
    purge_expired()
    res = json.loads(body)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    name = f"{res['ssp_name']} - {len(clause_ids)} clause{'s' if len(clause_ids) != 1 else ''}"
    with connect() as con:
        ensure_table(con)
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
        ensure_table(con)
        rows = con.execute("SELECT id, name, ssp_name, clause_ids, created_utc, config_status, embedder, summary "
                           "FROM runs WHERE user_id = ? ORDER BY created_utc DESC, id DESC", (user["id"],)).fetchall()
    return {"limit": MAX_RUNS, "runs": [{**dict(r), "clause_ids": r["clause_ids"].split(","),
                                         "summary": json.loads(r["summary"])} for r in rows]}


def _load(con, user: dict, run_id: int) -> tuple[dict, dict]:
    row = con.execute("SELECT id, name, created_utc, ssp_name, result FROM runs WHERE id = ? AND user_id = ?",
                      (run_id, user["id"])).fetchone()
    if not row:
        raise HTTPException(404, "That saved run was not found.")
    meta = {"id": row["id"], "name": row["name"], "created_utc": row["created_utc"], "ssp_name": row["ssp_name"]}
    return meta, json.loads(zlib.decompress(row["result"]))


@router.get("/export")
def export_runs(request: Request):
    """Everything stored about the signed-in user, as one JSON download."""
    user = _owner(request)
    with connect() as con:
        ensure_table(con)
        acct = con.execute("SELECT email, created_utc FROM users WHERE id = ?", (user["id"],)).fetchone()
        rows = con.execute("SELECT id, name, ssp_name, clause_ids, created_utc, config_status, embedder, summary, result "
                           "FROM runs WHERE user_id = ? ORDER BY created_utc", (user["id"],)).fetchall()
    data = {"exported_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "account": {"email": acct["email"], "created_utc": acct["created_utc"]},
            "note": "Your password is stored only as a one-way hash and is not included.",
            "runs": [{"id": r["id"], "name": r["name"], "ssp_name": r["ssp_name"], "clause_ids": r["clause_ids"].split(","),
                      "created_utc": r["created_utc"], "config_status": r["config_status"], "embedder": r["embedder"],
                      "summary": json.loads(r["summary"]), "result": json.loads(zlib.decompress(r["result"]))} for r in rows]}
    return Response(json.dumps(data, indent=1).encode(), media_type="application/json",
                    headers={"Content-Disposition": 'attachment; filename="pcef_my_data.json"'})


@router.get("/compare")
def compare_runs(a: int, b: int, request: Request):
    """Compare two of the user's runs; the older one is treated as 'before'."""
    user = _owner(request)
    if a == b:
        raise HTTPException(400, "Choose two different runs to compare.")
    with connect() as con:
        ensure_table(con)
        ma, ra = _load(con, user, a)
        mb, rb = _load(con, user, b)
    (m1, r1), (m2, r2) = sorted([(ma, ra), (mb, rb)], key=lambda x: (x[0]["created_utc"], x[0]["id"]))
    return {"before": m1, "after": m2, **compare(r1, r2)}


@router.get("/{run_id}")
def get_run(run_id: int, request: Request):
    user = _owner(request)
    with connect() as con:
        ensure_table(con)
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
        ensure_table(con)
        cur = con.execute("UPDATE runs SET name = ? WHERE id = ? AND user_id = ?", (name, run_id, user["id"]))
    if cur.rowcount == 0:
        raise HTTPException(404, "That saved run was not found.")
    return {"id": run_id, "name": name}


@router.delete("/{run_id}")
def delete_run(run_id: int, request: Request):
    user = _owner(request)
    with connect() as con:
        ensure_table(con)
        cur = con.execute("DELETE FROM runs WHERE id = ? AND user_id = ?", (run_id, user["id"]))
    if cur.rowcount == 0:
        raise HTTPException(404, "That saved run was not found.")
    return {"deleted": run_id}
