"""Plumbing only: no network, no API keys. Synthetic calls exercise the analysis."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run_json(tmp_path):
    from pcef.pipeline.run import DEFAULTS, run
    run(None, "tfidf", str(tmp_path / "rec"), *(str(ROOT / DEFAULTS[k]) for k in ("profiles", "catalog", "ssp", "config")))
    return tmp_path / "rec" / "run.json"


def test_dry_run_builds_prompts_without_calling(tmp_path):
    rj = _run_json(tmp_path)
    r = subprocess.run([sys.executable, str(ROOT / "validation/llm_baseline.py"), "--dry-run", "--run-json", str(rj),
                        "--anthropic-model", "a", "--openai-model", "o", "--gemini-model", "g"],
                       capture_output=True, text=True, cwd=str(ROOT))
    assert r.returncode == 0, r.stderr[-1500:]
    assert "x 5 runs x 3 models x 2 conditions" in r.stdout and "Reply with ONLY a JSON object" in r.stdout


def test_parse_handles_fences_and_rejects_bad():
    sys.path.insert(0, str(ROOT / "validation"))
    from llm_baseline import parse
    ok, _ = parse('```json\n{"alignment": 0.7, "realization": 0.4, "rationale": "x"}\n```')
    assert ok["alignment"] == 0.7
    assert parse('{"alignment": 1.4, "realization": 0.2}')[0] is None
    assert parse("no json here")[0] is None


def test_analysis_on_synthetic_calls(tmp_path):
    rj = _run_json(tmp_path)
    pairs = [f"{p['unit_id']}|{p['control_id']}" for p in json.loads(rj.read_text())["pairs"] if p["status"] == "scored"]
    calls = tmp_path / "calls.jsonl"
    with calls.open("w") as fh:
        for prov in ("anthropic", "openai", "gemini"):
            for cond in ("temp0", "default"):
                for i, p in enumerate(pairs):
                    for run_i in range(1, 6):
                        jitter = 0 if cond == "temp0" else 0.01 * run_i
                        fh.write(json.dumps({"provider": prov, "condition": cond, "pair": p, "run": run_i,
                                             "served_model": prov + "-x", "parsed": {"alignment": (i % 10) / 10,
                                             "realization": min(1, (i % 7) / 7 + jitter), "rationale": ""}}) + "\n")
    r = subprocess.run([sys.executable, str(ROOT / "validation/llm_analyse.py"), "--calls", str(calls),
                        "--run-json", str(rj), "--out", str(tmp_path / "an"), "--skip-pcef-repeat"],
                       capture_output=True, text=True, cwd=str(ROOT))
    assert r.returncode == 0, r.stderr[-1500:]
    d = json.loads((tmp_path / "an" / "llm_analysis.json").read_text())
    t0 = [x for x in d["rows"] if x["condition"] == "temp0"]
    assert all(x["pct_identical"] == 100.0 for x in t0)


def test_chat_prompts_parse_and_analyse(tmp_path):
    rj = _run_json(tmp_path)
    d = tmp_path / "chat"
    r = subprocess.run([sys.executable, str(ROOT / "validation/llm_chat_prompts.py"), "--run-json", str(rj), "--out", str(d)],
                       capture_output=True, text=True, cwd=str(ROOT))
    assert r.returncode == 0, r.stderr[-1500:]
    man = json.loads((d / "manifest.json").read_text())
    assert "pair_id:" in (d / "prompts" / "batch1.txt").read_text()
    for app in ("claude", "chatgpt", "gemini"):
        for run_i in (1, 2, 3):
            for b, info in man["batches"].items():
                arr = [{"pair_id": p, "alignment": 0.5, "realization": 0.1 * run_i, "rationale": "x"} for p in info["pairs"]]
                if app == "gemini" and run_i == 3:
                    arr = arr[:-1]                      # a missing pair must be recorded, not filled
                (d / "responses" / f"{app}_run{run_i}_{b}.txt").write_text("```json\n" + json.dumps(arr) + "\n```")
    r = subprocess.run([sys.executable, str(ROOT / "validation/llm_chat_parse.py"), "--dir", str(d)],
                       capture_output=True, text=True, cwd=str(ROOT))
    assert r.returncode == 0, r.stderr[-1500:]
    calls = [json.loads(l) for l in (d / "calls.jsonl").read_text().splitlines()]
    assert sum(1 for c in calls if c["parsed"] is None) == 2   # gemini run3: one missing pair per batch
    r = subprocess.run([sys.executable, str(ROOT / "validation/llm_analyse.py"), "--calls", str(d / "calls.jsonl"),
                        "--run-json", str(rj), "--out", str(d / "an"), "--skip-pcef-repeat"],
                       capture_output=True, text=True, cwd=str(ROOT))
    assert r.returncode == 0, r.stderr[-1500:]
