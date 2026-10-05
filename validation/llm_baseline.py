"""
LLM baseline - data collection (see validation/LLM_BASELINE_PROTOCOL.md).

Scores the same clause-control pairs as the PCEF method-of-record run, with 3 hosted LLMs,
2 conditions (temperature 0 / provider default), N runs each. Plain HTTPS (stdlib only):
no SDKs, so SDK changes cannot silently alter the request.

Keys come from environment variables: ANTHROPIC_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY.

  # 1. check the prompt and the call count, no API calls:
  python validation/llm_baseline.py --dry-run --anthropic-model M1 --openai-model M2 --gemini-model M3
  # 2. pilot: 2 pairs x 1 run, to check keys and parsing:
  python validation/llm_baseline.py --limit-pairs 2 --runs 1 --anthropic-model M1 --openai-model M2 --gemini-model M3
  # 3. full run (resumable - rerun the same command after an interruption):
  python validation/llm_baseline.py --anthropic-model M1 --openai-model M2 --gemini-model M3

Every call is appended to outputs/llm_baseline/calls.jsonl immediately.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from pcef.models import PDPAProfileSet
from pcef.parsers import CatalogIndex, SspDocument, normalize_control
from pcef.pipeline.measures import row_text
from pcef.pipeline.run import DEFAULTS

ROOT = Path(__file__).resolve().parents[1]
PROMPT_VERSION = "llm-baseline-prompt v1 (2026-10-05)"
SYSTEM = "You are an experienced information security and data protection compliance assessor."
TEMPLATE = """Assess how one security control relates to one legal obligation from Sri Lanka's Personal Data Protection Act No. 9 of 2022.

## Legal clause (verbatim)
{clause_text}

## The specific obligation being assessed
{obligation}
Elements the obligation requires:
{attributes}

## Security control (NIST SP 800-53 Rev 5, {control_id}: {control_title})
{control_text}

## The organization's implementation of this control (from its System Security Plan)
{ssp_text}

Give two separate scores between 0 and 1:

- "alignment": does the CONTROL, as written in the catalog, address the obligation on paper?
  0 = not at all; 1 = it addresses every element of the obligation. Ignore the implementation here.
- "realization": how fully and specifically has the organization IMPLEMENTED this control, judging only
  the implementation text? 0 = nothing implemented or described; 1 = fully and specifically implemented.

Reply with ONLY a JSON object, no other text:
{{"alignment": <number 0-1>, "realization": <number 0-1>, "rationale": "<at most 3 sentences>"}}"""


def build_items(run_json: Path, limit: int | None):
    """The exact pairs PCEF scored in the method-of-record run, with information parity."""
    run = json.loads(run_json.read_text(encoding="utf-8"))
    prof = PDPAProfileSet.from_json_file(str(ROOT / DEFAULTS["profiles"]))
    units = {u.unit_id: (c, u) for c in prof.clauses for u in c.obligation_units}
    ix = CatalogIndex.from_file(str(ROOT / DEFAULTS["catalog"]))
    ssp = SspDocument.from_file(str(ROOT / DEFAULTS["ssp"]))
    items = []
    for p in run["pairs"]:
        if p["status"] != "scored":
            continue
        clause, unit = units[p["unit_id"]]
        nc = normalize_control(p["control_id"], ix, ssp)
        ctl = "\n".join(f"- {sp.smt_id}: {row_text(nc, sp).split(': ', 1)[-1]}" for sp in nc.sub_parts)
        sc = ssp.get(p["control_id"])
        impl = "(The System Security Plan does not address this control.)"
        if sc:
            lines = [f"- {sid}: {b.description}" + (f" [remarks: {st.remarks}]" if st.remarks else "")
                     for sid, st in sorted(sc.statements.items()) for b in st.by_components]
            impl = "\n".join(lines) or impl
        prompt = TEMPLATE.format(
            clause_text=clause.verbatim_text, obligation=f"{unit.action}. {unit.object}",
            attributes="\n".join(f"- {a.name}" for a in unit.attributes) or "- (none listed)",
            control_id=nc.control_id, control_title=nc.title, control_text=ctl, ssp_text=impl)
        items.append({"pair": f"{p['unit_id']}|{p['control_id']}", "prompt": prompt})
    return items[:limit] if limit else items


# ---------------- providers (plain HTTPS) ----------------

def _post(url, headers, body, timeout=120):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={**headers, "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def call_anthropic(model, prompt, temperature):
    body = {"model": model, "max_tokens": 600, "system": SYSTEM, "messages": [{"role": "user", "content": prompt}]}
    if temperature is not None:
        body["temperature"] = temperature
    r = _post("https://api.anthropic.com/v1/messages",
              {"x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01"}, body)
    return "".join(b.get("text", "") for b in r.get("content", [])), r.get("model", model), r


def call_openai(model, prompt, temperature):
    body = {"model": model, "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}]}
    if temperature is not None:
        body["temperature"] = temperature
    r = _post("https://api.openai.com/v1/chat/completions",
              {"authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"}, body)
    return r["choices"][0]["message"]["content"], r.get("model", model), r


def call_gemini(model, prompt, temperature):
    body = {"systemInstruction": {"parts": [{"text": SYSTEM}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}]}
    if temperature is not None:
        body["generationConfig"] = {"temperature": temperature}
    r = _post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
              {"x-goog-api-key": os.environ["GEMINI_API_KEY"]}, body)
    parts = r["candidates"][0]["content"]["parts"]
    return "".join(x.get("text", "") for x in parts), r.get("modelVersion", model), r


PROVIDERS = {"anthropic": call_anthropic, "openai": call_openai, "gemini": call_gemini}
CONDITIONS = {"temp0": 0.0, "default": None}


def parse(text):
    t = text.strip()
    if t.startswith("```"):
        t = t.strip("`").split("\n", 1)[-1].rsplit("```", 1)[0]
    s, e = t.find("{"), t.rfind("}")
    try:
        d = json.loads(t[s:e + 1])
        a, r = float(d["alignment"]), float(d["realization"])
        if not (0 <= a <= 1 and 0 <= r <= 1):
            return None, "score out of range"
        return {"alignment": a, "realization": r, "rationale": str(d.get("rationale", ""))}, ""
    except Exception as ex:  # noqa: BLE001 - every failure is recorded, never retried silently
        return None, f"parse error: {type(ex).__name__}"


def main(argv=None):
    ap = argparse.ArgumentParser()
    for p in PROVIDERS:
        ap.add_argument(f"--{p}-model", required=True, help=f"exact {p} model id to record")
    ap.add_argument("--runs", type=int, default=5)
    ap.add_argument("--limit-pairs", type=int, default=None)
    ap.add_argument("--run-json", default="outputs/run_method_of_record_v1_1/run.json")
    ap.add_argument("--out", default="outputs/llm_baseline")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--pause", type=float, default=1.0, help="seconds between calls")
    a = ap.parse_args(argv)

    items = build_items(ROOT / a.run_json, a.limit_pairs)
    models = {p: getattr(a, f"{p}_model") for p in PROVIDERS}
    total = len(items) * a.runs * len(PROVIDERS) * len(CONDITIONS)
    phash = hashlib.sha256((PROMPT_VERSION + SYSTEM + TEMPLATE).encode()).hexdigest()[:12]
    print(f"{len(items)} pairs x {a.runs} runs x {len(PROVIDERS)} models x {len(CONDITIONS)} conditions = {total} calls")
    print(f"prompt: {PROMPT_VERSION} | template hash {phash}")
    if a.dry_run:
        print("\n----- example prompt -----\n" + SYSTEM + "\n\n" + items[0]["prompt"])
        return

    out = ROOT / a.out; out.mkdir(parents=True, exist_ok=True)
    log = out / "calls.jsonl"
    done = set()
    if log.exists():
        for line in log.read_text(encoding="utf-8").splitlines():
            d = json.loads(line); done.add((d["provider"], d["condition"], d["pair"], d["run"]))
    n = 0
    with log.open("a", encoding="utf-8") as fh:
        for prov, fn in PROVIDERS.items():
            for cond, temp in CONDITIONS.items():
                for it in items:
                    for run_i in range(1, a.runs + 1):
                        n += 1
                        key = (prov, cond, it["pair"], run_i)
                        if key in done:
                            continue
                        rec = {"provider": prov, "requested_model": models[prov], "condition": cond,
                               "temperature": temp, "pair": it["pair"], "run": run_i, "prompt_hash": phash,
                               "prompt_version": PROMPT_VERSION,
                               "time_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}
                        t0 = time.time()
                        for attempt in range(3):
                            try:
                                text, served, raw = fn(models[prov], it["prompt"], temp)
                                parsed, err = parse(text)
                                rec.update({"served_model": served, "raw_text": text, "parsed": parsed,
                                            "error": err, "usage": raw.get("usage") or raw.get("usageMetadata")})
                                break
                            except urllib.error.HTTPError as e:
                                body = e.read().decode(errors="replace")[:500]
                                if e.code in (429, 500, 502, 503, 529) and attempt < 2:
                                    time.sleep(10 * (attempt + 1)); continue
                                rec.update({"parsed": None, "error": f"HTTP {e.code}: {body}"}); break
                            except Exception as e:  # noqa: BLE001
                                if attempt < 2:
                                    time.sleep(5); continue
                                rec.update({"parsed": None, "error": f"{type(e).__name__}: {e}"}); break
                        rec["latency_s"] = round(time.time() - t0, 2)
                        fh.write(json.dumps(rec) + "\n"); fh.flush()
                        print(f"[{n}/{total}] {prov} {cond} {it['pair']} run{run_i}: "
                              f"{'ok' if rec['parsed'] else rec['error'][:80]}")
                        time.sleep(a.pause)
    print("done ->", log)


if __name__ == "__main__":
    main()
