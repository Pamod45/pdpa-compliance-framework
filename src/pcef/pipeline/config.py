"""Load the versioned parameter files and record their SHA-256 fingerprints."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PipelineConfig:
    params: dict
    directionality: dict
    params_sha256: str
    directionality_sha256: str

    @classmethod
    def load(cls, config_dir: str | Path = "config") -> "PipelineConfig":
        d = Path(config_dir)
        p_raw = (d / "pcef_params.json").read_bytes()
        t_raw = (d / "directionality_table.json").read_bytes()
        return cls(
            params=json.loads(p_raw),
            directionality=json.loads(t_raw),
            params_sha256=hashlib.sha256(p_raw).hexdigest(),
            directionality_sha256=hashlib.sha256(t_raw).hexdigest(),
        )

    def per_embedder(self, key: str, embedder_name: str) -> float:
        return float(self.params[key][embedder_name])
