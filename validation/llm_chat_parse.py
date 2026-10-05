"""
Parse the pasted chat replies into calls.jsonl (same format the analysis reads).

  python validation/llm_chat_parse.py
  python validation/llm_analyse.py --calls outputs/llm_chat/calls.jsonl --out outputs/llm_chat

Every expected pair that is missing or unparseable is recorded as a failure, never filled in.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME = re.compile(r"^(?P<app>[a-z0-9-]+)_run(?P<run>\d+)_batch(?P<batch>\d+)\.txt$")


def extract_array(text: str):
    t = text.strip()
    t = re.sub(r"^```[a-zA-Z]*\s*|\s*```$", "", t)
    s, e = t.find("["), t.rfind("]")
    if s < 0 or e < 0:
        raise ValueError("no JSON array found")
    return json.loads(t[s:e + 1])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="outputs/llm_chat")
    a = ap.parse_args(argv)
    base = ROOT / a.dir
    manifest = json.loads((base / "manifest.json").read_text(encoding="utf-8"))
    log_rows = {}
    log = base / "responses" / "chat_log.csv"
    if log.exists():
        lines = log.read_text(encoding="utf-8").splitlines()
        hdr = lines[0].split(",")
        for ln in lines[1:]:
            v = dict(zip(hdr, ln.split(",")))
            if v.get("app"):
                log_rows[(v["app"], v.get("run", ""), v.get("batch", ""))] = v
    out, summary = [], []
    for f in sorted((base / "responses").glob("*.txt")):
        m = NAME.match(f.name)
        if not m:
            continue
        app, run, batch = m["app"], int(m["run"]), f"batch{m['batch']}"
        expected = manifest["batches"][batch]["pairs"]
        meta = log_rows.get((app, str(run), m["batch"]), {})
        try:
            arr = extract_array(f.read_text(encoding="utf-8"))
            got = {str(o.get("pair_id")): o for o in arr if isinstance(o, dict)}
            err_all = ""
        except Exception as ex:  # noqa: BLE001
            got, err_all = {}, f"unparseable reply: {type(ex).__name__}"
        ok = 0
        for p in expected:
            o, parsed, err = got.get(p), None, err_all or "pair missing from reply"
            if o is not None:
                try:
                    al, re_ = float(o["alignment"]), float(o["realization"])
                    if 0 <= al <= 1 and 0 <= re_ <= 1:
                        parsed, err = {"alignment": al, "realization": re_, "rationale": str(o.get("rationale", ""))}, ""
                        ok += 1
                    else:
                        err = "score out of range"
                except Exception:  # noqa: BLE001
                    err = "bad fields"
            out.append({"provider": app, "condition": "chat_default", "pair": p, "run": run, "batch": batch,
                        "served_model": meta.get("model_shown") or None, "date": meta.get("date"),
                        "parsed": parsed, "error": err, "source_file": f.name,
                        "prompt_sha256": manifest["batches"][batch]["sha256"]})
        extra = sorted(set(got) - set(expected))
        summary.append(f"{f.name}: {ok}/{len(expected)} parsed" + (f" | unexpected ids: {extra}" if extra else "")
                       + (f" | {err_all}" if err_all else ""))
    (base / "calls.jsonl").write_text("".join(json.dumps(r) + "\n" for r in out), encoding="utf-8")
    print("\n".join(summary) or "no response files found")
    print("->", base / "calls.jsonl")


if __name__ == "__main__":
    main()
