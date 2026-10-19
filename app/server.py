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

Explore: upload an SSP, pick clauses, run the frozen v1.1 pipeline, trace every score.
Panel:   the fixed panel pack (validation/build_panel_pack.py), blind rating first, answers saved.
The embedding model is loaded once at start-up and reused for every run.
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

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from pcef.parsers import SspDocument
from pcef.pipeline.embedder import make_embedder
from pcef.pipeline.run import DEFAULTS, run

from .enrich import ROOT, pair_context, profiles

EMBEDDER = os.environ.get("PCEF_EMBEDDER", "sbert")
MODEL_REVISION = os.environ.get("PCEF_MODEL_REVISION") or None
PANEL_PACK = ROOT / "outputs" / "panel" / "panel_items.json"
PANEL_OUT = Path(os.environ.get("PCEF_DATA_DIR", ROOT / "outputs" / "panel")) / "responses.jsonl"
PANEL_WRITES = os.environ.get("PCEF_PANEL_WRITES", "1") != "0"
MAX_UPLOAD_BYTES = int(os.environ.get("PCEF_MAX_UPLOAD_MB", "5")) * 1024 * 1024
STATIC = Path(__file__).resolve().parent / "static"
_lock = threading.Lock()

_state: dict = {}


@asynccontextmanager
async def lifespan(_app):
    _state["emb"] = make_embedder(EMBEDDER, revision=MODEL_REVISION)   # loaded once, reused for every run
    yield


app = FastAPI(title="PCEF", lifespan=lifespan)


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
            "clauses": [{"id": c.clause_id, "title": getattr(c, "title", "") or "", "units": len(c.obligation_units),
                         "domains": list(c.security_domains)} for c in profiles().clauses]}


@app.post("/api/run")
async def run_pipeline(clause_ids: str = Form(...), use_sample: bool = Form(False),
                       ssp: UploadFile | None = File(None)):
    ids = [c for c in clause_ids.split(",") if c]
    if not ids:
        raise HTTPException(400, "Pick at least one clause to run.")
    with tempfile.TemporaryDirectory() as td:
        if use_sample or ssp is None:
            ssp_path, ssp_name = str(ROOT / DEFAULTS["ssp"]), "FleetTrack sample SSP"
        else:
            ssp_path, ssp_name = str(Path(td) / "upload.json"), ssp.filename
            raw = await ssp.read()
            if len(raw) > MAX_UPLOAD_BYTES:
                raise HTTPException(413, f"The file is larger than {MAX_UPLOAD_BYTES // (1024 * 1024)} MB.")
            Path(ssp_path).write_bytes(raw)
            try:
                SspDocument.from_file(ssp_path)
            except Exception as ex:  # noqa: BLE001 - show the parser's own message
                raise HTTPException(400, f"This file is not an OSCAL SSP the parser accepts ({type(ex).__name__}: {ex}). "
                                         "Upload a JSON file with a top-level 'system-security-plan'.")
        with _lock:
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
    return JSONResponse(json.loads(json.dumps(res, default=str)))


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
