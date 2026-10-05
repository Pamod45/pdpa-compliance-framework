"""Write validation/variant_review.md: every by-component text, strong vs each variant (text only, no scores)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SET = sys.argv[1] if len(sys.argv) > 1 else "v1"
VDIR = {"v1": "fleettrack_variants", "v2": "fleettrack_variants_v2", "v3": "fleettrack_variants_v3"}[SET]
FILES = {"strong": ROOT / "data/raw/ssps/fleettrack/fleettrack_ssp.json",
         **{v: ROOT / f"data/raw/ssps/{VDIR}/fleettrack_{v}.json"
            for v in ("partial", "broken", "vague_padded", "swapped")}}


def bcs(p):
    s = json.loads(p.read_text(encoding="utf-8"))["system-security-plan"]
    return {(ir["control-id"], st["statement-id"], bc["uuid"]): bc["description"]
            for ir in s["control-implementation"]["implemented-requirements"]
            for st in ir.get("statements", []) for bc in st.get("by-components", [])}


T = {n: bcs(p) for n, p in FILES.items()}
L = [f"# Degraded variant review - set {SET} (text only - no scores computed)", "",
     "Read each block. *(deleted)* = statement removed in that variant.", ""]
for key in sorted(T["strong"]):
    L.append(f"## {key[0]} / {key[1]}")
    for n in FILES:
        L.append(f"- **{n}**: {T[n].get(key, '*(deleted)*')}")
    L.append("")
name = "variant_review.md" if SET == "v1" else f"variant_review_{SET}.md"
(ROOT / "validation" / name).write_text("\n".join(L), encoding="utf-8")
print("wrote validation/" + name)
