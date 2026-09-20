"""
Stage 6: combine per-pair measures into the (Alignment, Realization) tuple.

The tuple is the result of record. `product_reporting_only` is a display value
and is not used for gap attribution or validation.
"""

from __future__ import annotations

from typing import Optional


def alignment(measures: dict[str, Optional[float]], weights: dict[str, float]) -> tuple[float, dict]:
    used = {k: weights[k] for k in weights
            if not k.startswith("_") and weights[k] > 0 and measures.get(k) is not None}
    total = sum(used.values())
    if total == 0:
        return 0.0, {}
    eff = {k: w / total for k, w in used.items()}       # re-normalised effective weights
    return sum(eff[k] * measures[k] for k in eff), {k: round(v, 4) for k, v in eff.items()}


def tuple_view(a: float, r: Optional[float]) -> dict:
    r0 = 0.0 if r is None else r
    return {"alignment": round(a, 4), "realization": None if r is None else round(r, 4),
            "product_reporting_only": round(a * r0, 4)}
