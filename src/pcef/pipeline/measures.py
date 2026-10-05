"""
Stage 5: Alignment and Realization measures.

Alignment measures (Relatedness, Coverage, Strength Match, Directionality) are pair
properties and read only the clause unit and the catalog rows, never the SSP, so a
change in the SSP moves Realization but not Alignment. Realization (Maturity) reads
only the SSP side of the normalised control.

All thresholds and weights are read from config/.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Optional

from ..models import ByComponent, ClauseProfile, NormalizedControl, ObligationUnit, SubPart
from .embedder import Embedder


# ---------- text builders (shared by Relatedness and Coverage) ----------

def unit_text(unit: ObligationUnit, mode: str = "plain") -> str:
    """Text embedded for a unit. 'keywords' appends the annotated keywords (config: unit_text_mode)."""
    base = f"{unit.action}. {unit.object}"
    if mode == "keywords" and unit.keywords:
        return f"{base}. Keywords: {', '.join(unit.keywords)}"
    if mode not in ("plain", "keywords"):
        raise ValueError(f"unknown unit_text_mode {mode!r}")
    return base


def row_text(nc: NormalizedControl, sp: SubPart) -> str:
    # Prefix leaf prose with its ancestors' prose so list items keep their stem
    ctx = f"{sp.catalog_context} " if sp.catalog_context else ""
    return f"{nc.title}: {ctx}{sp.catalog_text}"


@dataclass
class MeasureResult:
    value: Optional[float]           # None = not applicable for this pair
    detail: dict = field(default_factory=dict)


# ---------- Relatedness ----------

def relatedness(emb: Embedder, unit: ObligationUnit, nc: NormalizedControl,
                text_mode: str = "plain") -> MeasureResult:
    # A pair's relatedness is its best-matching catalog row (max roll-up)
    ut = unit_text(unit, text_mode)
    scored = [(emb.similarity(ut, row_text(nc, sp)), sp.smt_id) for sp in nc.sub_parts]
    if not scored:
        return MeasureResult(0.0, {"reason": "control has no catalog rows"})
    best, best_row = max(scored)
    return MeasureResult(best, {"best_row": best_row,
                                "per_row": {r: round(s, 4) for s, r in scored}})


# ---------- Coverage ----------

def coverage(emb: Embedder, unit: ObligationUnit, nc: NormalizedControl, threshold: float,
             mode: str = "threshold", ramp: tuple[float, float] | None = None) -> MeasureResult:
    """Fraction of the unit's attributes the control's catalog rows address.

    mode 'threshold': attribute counts 1 if its best cosine >= threshold, else 0.
    mode 'ramp'     : attribute scores 0 at/below ramp[0], 1 at/above ramp[1], linear between.
    """
    if not unit.attributes:
        return MeasureResult(None, {"reason": "unit has no attributes"})
    if mode == "ramp":
        if ramp is None or not ramp[0] < ramp[1]:
            raise ValueError(f"ramp mode needs low < high, got {ramp!r}")
        lo, hi = ramp
    elif mode != "threshold":
        raise ValueError(f"unknown coverage_mode {mode!r}")
    rows = [(row_text(nc, sp), sp.smt_id) for sp in nc.sub_parts]
    per_attr = {}
    for a in unit.attributes:
        best, best_row = max(((emb.similarity(a.name, t), r) for t, r in rows), default=(0.0, None))
        score = (min(max((best - lo) / (hi - lo), 0.0), 1.0) if mode == "ramp"
                 else (1.0 if best >= threshold else 0.0))
        per_attr[a.attr_id] = {"name": a.name, "best": round(best, 4), "row": best_row,
                               "score": round(score, 4)}
    value = sum(v["score"] for v in per_attr.values()) / len(per_attr)
    detail = {"mode": mode, "total": len(per_attr), "attributes": per_attr}
    detail.update({"ramp": list(ramp)} if mode == "ramp" else {"threshold": threshold})
    return MeasureResult(value, detail)


# ---------- Strength Match ----------

def strength_match(unit: ObligationUnit, nc: NormalizedControl, params: dict) -> MeasureResult:
    required = params["modality_strength"].get(unit.modality)
    if required is None:
        return MeasureResult(None, {"reason": f"modality '{unit.modality}' has no strength demand"})
    cues = [c.lower() for c in params["catalog_hedge_cues"]]
    texts = [sp.catalog_text.lower() for sp in nc.sub_parts] or [""]
    hedged = [t for t in texts if any(c in t for c in cues)]
    control_strength = 1.0 - len(hedged) / len(texts)
    return MeasureResult(1.0 - abs(required - control_strength),
                         {"required": required, "control_strength": round(control_strength, 4),
                          "hedged_rows": len(hedged), "rows": len(texts)})


# ---------- Directionality ----------

def unit_orientation(clause: ClauseProfile, table: dict) -> Optional[str]:
    mapping = table["domain_orientation"]
    found = [mapping[d] for d in clause.security_domains if d in mapping]
    if not found:
        return None
    counts = Counter(found)
    top = max(counts.values())
    return next(o for o in found if counts[o] == top)   # tie -> first listed


def control_orientation(nc: NormalizedControl, table: dict) -> tuple[Optional[str], str]:
    overrides = table.get("control_orientation", {})
    base = nc.control_id.split(".")[0]
    for key, src in ((nc.control_id, "control_override"), (base, "base_control_override")):
        if key in overrides and not key.startswith("_"):
            return overrides[key], src
    return table["family_orientation"].get(nc.family.upper()), "family"


def directionality(clause: ClauseProfile, nc: NormalizedControl, table: dict) -> MeasureResult:
    uo = unit_orientation(clause, table)
    co, co_source = control_orientation(nc, table)
    if uo is None or co is None:
        return MeasureResult(table["unknown_default"],
                             {"unit_orientation": uo, "control_orientation": co, "orientation_source": co_source,
                              "used_default": True})
    cell = table["compatibility"][uo][co]
    expected = table["level_match"][uo]
    mismatch = nc.implementation_level is not None and nc.implementation_level != expected
    value = cell * (table["level_match"]["level_mismatch_factor"] if mismatch else 1.0)
    return MeasureResult(value, {"unit_orientation": uo, "control_orientation": co,
                                 "orientation_source": co_source,
                                 "cell": cell, "impl_level": nc.implementation_level,
                                 "expected_level": expected, "level_mismatch": mismatch})


# ---------- Maturity (Realization) ----------

_ARTEFACT_PATTERNS = [
    re.compile(r"\b\d+(?:\.\d+)+\b"),                                              # versions
    re.compile(r"\b[\w-]+\.(?:py|db|json|ya?ml|conf|md|log|sql|txt|toml|ini|env)\b", re.I),  # files
    re.compile(r"\b(?:AES|TLS|SHA-?\d*|bcrypt|RSA|HMAC|JWT|OAuth2?|SSH|HTTPS|PBKDF2|argon2)\b", re.I),
    re.compile(r"\b\d+\s*(?:seconds?|minutes?|hours?|days?|weeks?|months?|years?)\b", re.I),  # durations
    re.compile(r"\b[a-z]+_[a-z0-9_]+\b"),                                         # code identifiers
]


def _by_component_score(b: ByComponent, mp: dict) -> tuple[float, dict]:
    text = f"{b.description} {b.remarks or ''}"
    words = len(text.split())
    artefacts = {m.group(0) for p in _ARTEFACT_PATTERNS for m in p.finditer(text)}
    neg_hits = [c for c in mp["negation_cues"] if c in text.lower()]
    f = {
        "specificity": min(words / mp["specificity_full_words"], 1.0),
        "concrete_artefacts": min(len(artefacts) / mp["artefacts_full_count"], 1.0),
        "set_parameters": 1.0 if b.set_parameters else 0.0,
        "operational_component": 1.0 if b.component_status == "operational" else 0.0,
        "commitment": 0.0 if neg_hits else 1.0,
    }
    w = mp["feature_weights"]
    uncapped = sum(w[k] * f[k] for k in w)
    # Declared-gap cap: text stating the control is not done is capped, however detailed
    capped = bool(neg_hits) and uncapped > mp["declared_gap_cap"]
    score = min(uncapped, mp["declared_gap_cap"]) if neg_hits else uncapped
    return score, {"features": {k: round(v, 3) for k, v in f.items()},
                   "artefacts": sorted(artefacts)[:10], "negation_hits": neg_hits,
                   "uncapped": round(uncapped, 4), "capped": capped, "score": round(score, 4)}


def _relative_factor(emb, text: str, nc: NormalizedControl, reference: dict, rel_cfg: dict) -> tuple[float, dict]:
    """Relative relevance: z-score of the text's similarity to its own control against the SSP's other controls."""
    own = max((emb.similarity(text, row_text(nc, sp)) for sp in nc.sub_parts), default=0.0)
    others = [max(emb.similarity(text, t) for t in rows) for cid, rows in reference.items()
              if cid != nc.control_id and rows]
    if len(others) < rel_cfg["min_reference_controls"]:
        return 1.0, {"relevance_mode": "relative", "relevance_skipped": f"only {len(others)} other controls"}
    mean = sum(others) / len(others)
    sd = (sum((o - mean) ** 2 for o in others) / len(others)) ** 0.5
    z = (own - mean) / sd if sd > 0 else 0.0
    factor = min(max(z / rel_cfg["z_full"], 0.0), 1.0)
    return factor, {"relevance_mode": "relative", "own_cosine": round(own, 4), "others_mean": round(mean, 4),
                    "others_sd": round(sd, 4), "z": round(z, 3), "relevance_factor": round(factor, 4)}


def maturity(nc: NormalizedControl, params: dict, emb: Optional[Embedder] = None,
             reference: Optional[dict] = None) -> MeasureResult:
    """`reference` maps control_id to catalog row texts for every SSP control (relative relevance only)."""
    mp = params["maturity"]
    if mp["horizontal_rule"] != "max" or mp["vertical_rule"] != "mean_excluding_na":
        raise ValueError("only the rules 'max' / 'mean_excluding_na' are implemented")
    rel_cfg = mp.get("relevance", {"enabled": False})
    use_rel = bool(rel_cfg.get("enabled"))
    rel_mode = rel_cfg.get("mode", "absolute")
    if use_rel:
        if emb is None:
            raise ValueError("maturity.relevance is enabled but no embedder was given")
        if rel_mode == "absolute":
            lo, hi = rel_cfg["ramp"][emb.name]
        elif rel_mode == "relative":
            if reference is None:
                raise ValueError("relative relevance needs the SSP's reference controls")
        else:
            raise ValueError(f"unknown relevance mode {rel_mode!r}")

    rows = {}
    counted: list[float] = []
    for sp in nc.sub_parts:
        if sp.status == "na":
            rows[sp.smt_id] = {"status": "na", "score": None}
            continue
        if sp.status == "absent" or not sp.by_components:
            rows[sp.smt_id] = {"status": sp.status, "score": 0.0}
            counted.append(0.0)
            continue
        scored = []
        for b in sp.by_components:
            sc, d = _by_component_score(b, mp)
            if use_rel and rel_mode == "absolute":
                # Absolute relevance: similarity of the text to the row it is attached to
                cos = emb.similarity(b.description, row_text(nc, sp))
                factor = min(max((cos - lo) / (hi - lo), 0.0), 1.0)
                d.update({"relevance_cosine": round(cos, 4), "relevance_factor": round(factor, 4),
                          "score_before_relevance": round(sc, 4)})
                sc *= factor
                d["score"] = round(sc, 4)
            elif use_rel and rel_mode == "relative":
                factor, info = _relative_factor(emb, b.description, nc, reference, rel_cfg)
                d.update(info); d["score_before_relevance"] = round(sc, 4)
                sc *= factor
                d["score"] = round(sc, 4)
            scored.append((sc, d))
        # Horizontal rule: several by-components in one row collapse to their max
        row_score = max(s for s, _ in scored)
        if sp.status == "inherited":
            row_score *= mp["inheritance_discount"]   # inherited text gets partial credit
        rows[sp.smt_id] = {"status": sp.status, "source": sp.source_smt_id,
                           "score": round(row_score, 4),
                           "by_components": [d for _, d in scored]}
        counted.append(row_score)

    # Vertical rule: mean over rows, na excluded, absent counted as 0
    value = sum(counted) / len(counted) if counted else None
    return MeasureResult(value, {"rows": rows, "counted_rows": len(counted), "relevance": use_rel,
                                 "rules": ["horizontal=max", "vertical=mean_excluding_na"]})
