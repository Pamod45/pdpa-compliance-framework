"""
Chat-based LLM baseline (protocol amendment 2026-10-05): build the batch prompts you paste into each chat app.

  python validation/llm_chat_prompts.py

Writes outputs/llm_chat/prompts/batch1.txt, batch2.txt and an empty responses/ folder with naming rules.
Same information per pair as the API design (information parity with PCEF); pairs in a fixed order.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "validation"))
from llm_baseline import SYSTEM, build_items  # noqa: E402  (same per-pair content as the API design)

CHAT_VERSION = "llm-chat-batch-prompt v1 (2026-10-05)"
HEADER = """{system}

You will assess {n} separate clause-control pairs. Assess EACH pair on its own; do not let one pair influence another.
For each pair give two scores between 0 and 1:
- "alignment": does the CONTROL, as written in the catalog, address the obligation on paper? 0 = not at all; 1 = it addresses every element. Ignore the implementation.
- "realization": how fully and specifically has the organization IMPLEMENTED this control, judging only the implementation text? 0 = nothing implemented or described; 1 = fully and specifically implemented.

Reply with ONLY a JSON array, one object per pair, in the same order, no other text:
[{{"pair_id": "<as given>", "alignment": <0-1>, "realization": <0-1>, "rationale": "<at most 2 sentences>"}}, ...]
"""


def strip_item(prompt: str) -> str:
    """Keep the pair-specific sections of the single-pair prompt (drop its own instructions)."""
    body = prompt.split("Give two separate scores", 1)[0]
    return body.replace("Assess how one security control relates to one legal obligation from Sri Lanka's "
                        "Personal Data Protection Act No. 9 of 2022.\n\n", "").strip()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-json", default="outputs/run_method_of_record_v1_1/run.json")
    ap.add_argument("--out", default="outputs/llm_chat")
    ap.add_argument("--batches", type=int, default=2)
    a = ap.parse_args(argv)
    items = build_items(ROOT / a.run_json, None)
    out = ROOT / a.out; (out / "prompts").mkdir(parents=True, exist_ok=True); (out / "responses").mkdir(exist_ok=True)
    size = -(-len(items) // a.batches)
    manifest = {"version": CHAT_VERSION, "batches": {}}
    for b in range(a.batches):
        chunk = items[b * size:(b + 1) * size]
        text = HEADER.format(system=SYSTEM, n=len(chunk)) + "\nPairs (Sri Lanka Personal Data Protection Act No. 9 of 2022 vs NIST SP 800-53 Rev 5):\n"
        for it in chunk:
            text += f"\n==================== pair_id: {it['pair']} ====================\n{strip_item(it['prompt'])}\n"
        (out / "prompts" / f"batch{b + 1}.txt").write_text(text, encoding="utf-8")
        manifest["batches"][f"batch{b + 1}"] = {"pairs": [it["pair"] for it in chunk],
                                                "sha256": hashlib.sha256(text.encode()).hexdigest()[:12],
                                                "chars": len(text)}
        print(f"batch{b + 1}: {len(chunk)} pairs, {len(text):,} chars")
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (out / "responses" / "README.txt").write_text(
        "Save each reply EXACTLY as received (copy the whole reply) as:\n"
        "  <app>_run<r>_batch<b>.txt   e.g.  claude_run1_batch1.txt, chatgpt_run3_batch2.txt, gemini_run2_batch1.txt\n"
        "Then fill one line per chat in chat_log.csv (app, model name shown in the app, date, run, batch, notes).\n",
        encoding="utf-8")
    log = out / "responses" / "chat_log.csv"
    if not log.exists():
        log.write_text("app,model_shown,date,run,batch,temporary_or_memory_off,notes\n", encoding="utf-8")
    print("prompts ->", out / "prompts")


if __name__ == "__main__":
    main()
