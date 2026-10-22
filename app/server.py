"""
PCEF local UI server: FastAPI backend + the pre-built React frontend.

  python -m app.server            (opens http://127.0.0.1:8000)

Environment variables (all optional; defaults suit a local run):
  HOST, PORT               bind address and port (default 127.0.0.1:8000)
  PCEF_EMBEDDER            sbert (default) or tfidf
  PCEF_MODEL_REVISION      pin the embedding model to an exact revision
  PCEF_DATA_DIR            where panel responses are written (default outputs/panel)
  PCEF_PANEL_WRITES        set to 0 to stop accepting panel responses
  PCEF_MAX_UPLOAD_MB       largest SSP upload accepted (default 5)
  PCEF_OPEN_BROWSER        set to 0 to stop opening a browser on start-up
  PCEF_WARM_SAMPLE         set to 0 to skip scoring the sample in the background on start-up
  PCEF_DB                  account database file (default <PCEF_DATA_DIR>/pcef.sqlite3, else instance/)
  PCEF_RETENTION_DAYS      days a saved run is kept (default 365; 0 keeps runs until the user deletes them)

Explore: upload an SSP, pick clauses, run the frozen v1.1 pipeline, trace every score.
Panel:   the fixed panel pack (validation/build_panel_pack.py), blind rating first, answers saved.
The embedding model is loaded once at start-up and reused for every run. Sample runs are
cached by clause set, and the all-clause sample is scored in the background on start-up,
so the sample opens without waiting for the model.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
import webbrowser
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel

from pcef.parsers import SspDocument
from pcef.pipeline.embedder import make_embedder
from pcef.pipeline.gates import ROLE_PROP, applicability_gate, parse_roles
from pcef.pipeline.run import DEFAULTS, run

from . import auth, history
from .enrich import ROOT, pair_context, profiles, unit_lookup

EMBEDDER = os.environ.get("PCEF_EMBEDDER", "sbert")
MODEL_REVISION = os.environ.get("PCEF_MODEL_REVISION") or None
PANEL_PACK = ROOT / "outputs" / "panel" / "panel_items.json"
PANEL_OUT = Path(os.environ.get("PCEF_DATA_DIR", ROOT / "outputs" / "panel")) / "responses.jsonl"
PANEL_WRITES = os.environ.get("PCEF_PANEL_WRITES", "1") != "0"
MAX_UPLOAD_BYTES = int(os.environ.get("PCEF_MAX_UPLOAD_MB", "5")) * 1024 * 1024
WARM_SAMPLE = os.environ.get("PCEF_WARM_SAMPLE", "1") != "0"
SAMPLE_CACHE_SIZE = 8
STATIC = Path(__file__).resolve().parent / "static"
_lock = threading.Lock()          # one pipeline run at a time
_sample_lock = threading.Lock()   # a sample request waits for the warm-up instead of repeating it

_state: dict = {}
_sample_cache: dict[tuple[str, ...], bytes] = {}   # sorted clause ids -> serialised sample result


def _score(ids: list[str], ssp_path: str, ssp_name: str) -> bytes:
    with tempfile.TemporaryDirectory() as td, _lock:
        res = run(ids, EMBEDDER, str(Path(td) / "out"), *(str(ROOT / DEFAULTS[k]) for k in ("profiles", "catalog")),
                  ssp_path, str(ROOT / DEFAULTS["config"]), emb=_state["emb"])
    for p in res["pairs"]:
        p["context"] = pair_context(p["unit_id"], p["control_id"], ssp_path)
    # every obligation unit of the chosen clauses, so the overview can show units with no pair too
    res["units"] = [{"unit_id": u.unit_id, "clause_id": c.clause_id, "clause_title": getattr(c, "title", "") or "",
                     "obligation": f"{u.action}. {u.object}", "scored": u.scored,
                     "unit_type": u.unit_type, "modality": u.modality}
                    for c in profiles().clauses if c.clause_id in ids for u in c.obligation_units]
    res["ssp_name"] = ssp_name
    return json.dumps(res, default=str).encode("utf-8")


def _sample(ids: list[str]) -> bytes:
    key = tuple(sorted(ids))
    with _sample_lock:
        if key not in _sample_cache:
            body = _score(list(key), str(ROOT / DEFAULTS["ssp"]), "FleetTrack sample SSP")
            if len(_sample_cache) >= SAMPLE_CACHE_SIZE:
                _sample_cache.pop(next(iter(_sample_cache)))
            _sample_cache[key] = body
        return _sample_cache[key]


def _warm():
    try:
        _sample([c.clause_id for c in profiles().clauses])
    except Exception as ex:  # noqa: BLE001 - a failed warm-up only means the first sample run is slower
        print(f"PCEF: background sample run failed: {type(ex).__name__}: {ex}")


@asynccontextmanager
async def lifespan(_app):
    _state["emb"] = make_embedder(EMBEDDER, revision=MODEL_REVISION)   # loaded once, reused for every run
    history.purge_expired()
    if WARM_SAMPLE:
        threading.Thread(target=_warm, daemon=True).start()
    yield


app = FastAPI(title="PCEF", lifespan=lifespan)
app.include_router(auth.router)
app.include_router(history.router)


@app.get("/api/meta")
def meta():
    cfg = json.loads((ROOT / DEFAULTS["config"] / "pcef_params.json").read_text(encoding="utf-8"))
    emb = _state["emb"]
    mp = cfg["maturity"]
    return {"config_status": cfg["_status"].split(" - ")[0], "embedder": emb.model_id, "revision": emb.revision,
            "constants": {"feature_weights": mp["feature_weights"], "inheritance_discount": mp["inheritance_discount"],
                          "declared_gap_cap": mp["declared_gap_cap"], "coverage_ramp": cfg["coverage_ramp"][emb.name],
                          "relatedness_floor": cfg["relatedness_floor"][emb.name],
                          "alignment_weights": {k: v for k, v in cfg["alignment_weights"].items() if not k.startswith("_")}},
            "panel_available": PANEL_PACK.exists(),
            "retention_days": history.retention_days(),
            "sample_ready": tuple(sorted(c.clause_id for c in profiles().clauses)) in _sample_cache,
            "clauses": [{"id": c.clause_id, "title": getattr(c, "title", "") or "", "units": len(c.obligation_units),
                         "domains": list(c.security_domains)} for c in profiles().clauses]}


@app.post("/api/run")
async def run_pipeline(request: Request, clause_ids: str = Form(...), use_sample: bool = Form(False),
                       ssp: UploadFile | None = File(None)):
    ids = [c for c in clause_ids.split(",") if c]
    if not ids:
        raise HTTPException(400, "Pick at least one clause to run.")
    user = auth.current_user(request)        # signed-in runs are saved to the user's history
    if use_sample or ssp is None:
        body = await run_in_threadpool(_sample, ids)
        return Response(history.save(user, body, ids) if user else body, media_type="application/json")
    raw = await ssp.read()
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, f"The file is larger than {MAX_UPLOAD_BYTES // (1024 * 1024)} MB.")
    with tempfile.TemporaryDirectory() as td:
        ssp_path = str(Path(td) / "upload.json")
        Path(ssp_path).write_bytes(raw)
        try:
            SspDocument.from_file(ssp_path)
        except Exception as ex:  # noqa: BLE001 - show the parser's own message
            raise HTTPException(400, f"This file is not an OSCAL SSP the parser accepts ({type(ex).__name__}: {ex}). "
                                     "Upload a JSON file with a top-level 'system-security-plan'.")
        body = await run_in_threadpool(_score, ids, ssp_path, ssp.filename)
        return Response(history.save(user, body, ids) if user else body, media_type="application/json")


# The walkthrough follows one duty (s.10, integrity and confidentiality) with two of the controls
# its clause profile names directly: AC-3 is described as built, SC-28 is declared a known gap.
WALK = [("s10-u1", "ac-3"), ("s10-u1", "sc-28")]


@app.get("/api/walkthrough")
async def walkthrough():
    ids = sorted({unit_lookup()[u][0].clause_id for u, _ in WALK})
    res = json.loads(await run_in_threadpool(_sample, ids))
    raw = json.loads((ROOT / DEFAULTS["ssp"]).read_text(encoding="utf-8"))["system-security-plan"]
    chars = raw["system-characteristics"]
    role_raw = next((pr["value"] for pr in chars.get("props", []) if pr["name"] == ROLE_PROP), None)
    reqs = {ir["control-id"]: ir for ir in raw["control-implementation"]["implemented-requirements"]}
    cases = []
    for unit_id, control_id in WALK:
        clause, unit = unit_lookup()[unit_id]
        pair = next(p for p in res["pairs"] if p["unit_id"] == unit_id and p["control_id"] == control_id)
        other = applicability_gate(unit, frozenset({"processor"}), "example")   # the same duty for a processor-only plan
        cases.append({
            "clause": {"id": clause.clause_id, "title": clause.title, "text": clause.verbatim_text,
                       "simplified": clause.simplified_text},
            "unit": unit.model_dump(include={"unit_id", "unit_type", "actor", "modality", "action", "object",
                                             "attributes", "keywords", "control_hints", "applicability_conditions"}),
            "candidates": [{"control_id": p["control_id"], "title": p["control_title"], "source": p["pair_source"],
                            "status": p["status"], "tuple": p.get("tuple")}
                           for p in res["pairs"] if p["unit_id"] == unit_id],
            "pair": pair,
            "realization": res["realization"][control_id],
            "ssp_entry": reqs.get(control_id),
            "role_check_other": {"roles": ["processor"], "passed": other.passed, "reason": other.reason},
        })
    return {"ssp": {"name": chars.get("system-name"), "role": role_raw, "roles": sorted(parse_roles(role_raw) or []),
                    "controls": len(reqs), "components": len(raw.get("system-implementation", {}).get("components", []))},
            "clauses_loaded": len(profiles().clauses), "provenance": res["provenance"], "cases": cases}


@app.get("/api/sample-ssp")
def sample_ssp():
    return FileResponse(ROOT / DEFAULTS["ssp"], media_type="application/json", filename="fleettrack_ssp.json")


@app.get("/api/panel/items")
def panel_items():
    if not PANEL_PACK.exists():
        raise HTTPException(404, "No panel pack yet. Run: python validation/build_panel_pack.py")
    return json.loads(PANEL_PACK.read_text(encoding="utf-8"))


class PanelResponse(BaseModel):
    expert: str
    pair: str
    pack_sha256: str
    blind_alignment: float
    blind_realization: float
    confidence: str
    blind_note: str = ""
    defensible_alignment: str
    defensible_realization: str
    reveal_note: str = ""
    seconds_blind: float | None = None


@app.post("/api/panel/response")
def panel_response(r: PanelResponse):
    if not PANEL_WRITES:
        raise HTTPException(403, "Panel responses are closed on this deployment.")
    if not (0 <= r.blind_alignment <= 1 and 0 <= r.blind_realization <= 1):
        raise HTTPException(400, "Ratings must be between 0 and 1.")
    PANEL_OUT.parent.mkdir(parents=True, exist_ok=True)
    rec = {**r.model_dump(), "saved_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    with _lock, PANEL_OUT.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec) + "\n")
    return {"saved": True}


@app.get("/api/panel/progress")
def panel_progress(expert: str):
    if not PANEL_OUT.exists():
        return {"done": []}
    done = [json.loads(l)["pair"] for l in PANEL_OUT.read_text(encoding="utf-8").splitlines()
            if l.strip() and json.loads(l)["expert"] == expert]
    return {"done": sorted(set(done))}


if STATIC.exists():
    app.mount("/assets", StaticFiles(directory=STATIC / "assets"), name="assets")

    @app.get("/{path:path}")
    def spa(path: str):
        f = STATIC / path
        return FileResponse(f if path and f.is_file() else STATIC / "index.html")


def main():
    import uvicorn
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    if os.environ.get("PCEF_OPEN_BROWSER", "1") != "0":
        threading.Timer(2.5, lambda: webbrowser.open(f"http://127.0.0.1:{port}")).start()
    uvicorn.run(app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    main()
