"""Readable context for a clause-control pair: the law text, the catalog rows, the SSP text."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pcef.models import PDPAProfileSet
from pcef.parsers import CatalogIndex, SspDocument, normalize_control
from pcef.pipeline.measures import row_text
from pcef.pipeline.run import DEFAULTS

ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def catalog():
    return CatalogIndex.from_file(str(ROOT / DEFAULTS["catalog"]))


@lru_cache(maxsize=1)
def profiles():
    return PDPAProfileSet.from_json_file(str(ROOT / DEFAULTS["profiles"]))


def unit_lookup():
    return {u.unit_id: (c, u) for c in profiles().clauses for u in c.obligation_units}


def ssp_texts(ssp: SspDocument, control_id: str) -> list[dict]:
    sc = ssp.get(control_id)
    if not sc:
        return []
    return [{"statement": sid, "text": b.description, "remarks": st.remarks}
            for sid, st in sorted(sc.statements.items()) for b in st.by_components]


def pair_context(unit_id: str, control_id: str, ssp_path: str | None = None) -> dict:
    clause, unit = unit_lookup()[unit_id]
    ssp = SspDocument.from_file(ssp_path or str(ROOT / DEFAULTS["ssp"]))
    nc = normalize_control(control_id, catalog(), ssp)
    return {
        "clause_id": clause.clause_id, "clause_title": getattr(clause, "title", "") or "",
        "clause_text": clause.verbatim_text, "obligation": f"{unit.action}. {unit.object}",
        "modality": unit.modality, "actor": unit.actor,
        "attributes": [a.name for a in unit.attributes],
        "control_id": control_id, "control_title": nc.title,
        "catalog_rows": [{"id": sp.smt_id, "text": row_text(nc, sp).split(": ", 1)[-1]} for sp in nc.sub_parts],
        "ssp_text": ssp_texts(ssp, control_id),
    }
