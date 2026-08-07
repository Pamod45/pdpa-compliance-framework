"""Stage 2 parsers: OSCAL catalog and SSP -> NormalizedControl."""

from .catalog import CatalogControl, CatalogIndex, StatementNode
from .fuse import (
    NormalizationReport,
    declares_na,
    normalize_all,
    normalize_control,
)
from .ssp import (
    Component,
    SspByComponent,
    SspControl,
    SspDocument,
    SspIntegrityError,
    SspStatement,
)

__all__ = [
    # catalog side (normative)
    "CatalogControl",
    "CatalogIndex",
    "StatementNode",
    # SSP side (organizational)
    "Component",
    "SspByComponent",
    "SspControl",
    "SspDocument",
    "SspIntegrityError",
    "SspStatement",
    # fuse (A3)
    "NormalizationReport",
    "declares_na",
    "normalize_all",
    "normalize_control",
]
