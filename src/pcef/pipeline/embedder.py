"""
Text embedders used by the relatedness floor, Relatedness and Coverage.

SbertEmbedder  sentence-transformers model; used for all reported results.
TfidfEmbedder  TF-IDF stand-in for tests and offline runs. Its scores are on a
               different scale and are not used for reported results.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Protocol

DEFAULT_SBERT_MODEL = "sentence-transformers/all-mpnet-base-v2"


class Embedder(Protocol):
    name: str          # "sbert" | "tfidf"; also the key for per-embedder config values
    model_id: str      # exact model identity, recorded in provenance
    revision: str      # resolved model revision (commit hash) or "n/a"

    def fit(self, texts: list[str]) -> None: ...
    def similarity(self, a: str, b: str) -> float: ...


class SbertEmbedder:
    name = "sbert"

    def __init__(self, model_id: str = DEFAULT_SBERT_MODEL, revision: str | None = None):
        from sentence_transformers import SentenceTransformer  # imported lazily: heavy

        self.model_id = model_id
        self._model = SentenceTransformer(model_id, revision=revision, device="cpu")
        self.revision = revision or _resolved_revision(model_id)
        self._cache: dict[str, object] = {}

    def fit(self, texts: list[str]) -> None:
        todo = [t for t in dict.fromkeys(texts) if t not in self._cache]
        if todo:
            vecs = self._model.encode(todo, normalize_embeddings=True, batch_size=32,
                                      show_progress_bar=False)
            self._cache.update(zip(todo, vecs))

    def similarity(self, a: str, b: str) -> float:
        self.fit([a, b])
        va, vb = self._cache[a], self._cache[b]
        return float(sum(float(x) * float(y) for x, y in zip(va, vb)))  # unit vectors -> dot = cosine


def _resolved_revision(model_id: str) -> str:
    """Commit hash of the locally cached model snapshot, for provenance."""
    try:
        from huggingface_hub import snapshot_download

        path = snapshot_download(model_id, local_files_only=True)
        return path.replace("\\", "/").rstrip("/").split("/")[-1]
    except Exception:  # noqa: BLE001 - provenance lookup must not stop a run
        return "unknown"


_TOKEN = re.compile(r"[a-z0-9]+")
_STOP = frozenset(
    "a an the of and or to for in on by with as at be is are any such that this these those "
    "from into its it which following".split()
)


def _tokens(text: str) -> list[str]:
    return [t for t in _TOKEN.findall(text.lower()) if t not in _STOP and len(t) > 1]


class TfidfEmbedder:
    """TF-IDF cosine over the texts given to fit(). Stand-in only."""

    name = "tfidf"
    model_id = "tfidf-standin"
    revision = "n/a"

    def __init__(self) -> None:
        self._idf: dict[str, float] = {}

    def fit(self, texts: list[str]) -> None:
        docs = [set(_tokens(t)) for t in dict.fromkeys(texts)]
        n = len(docs) or 1
        df = Counter(tok for d in docs for tok in d)
        self._idf = {tok: math.log((1 + n) / (1 + c)) + 1.0 for tok, c in df.items()}

    def _vec(self, text: str) -> dict[str, float]:
        tf = Counter(_tokens(text))
        v = {t: c * self._idf.get(t, 1.0) for t, c in tf.items()}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        return {t: x / norm for t, x in v.items()}

    def similarity(self, a: str, b: str) -> float:
        va, vb = self._vec(a), self._vec(b)
        return sum(x * vb.get(t, 0.0) for t, x in va.items())


def make_embedder(kind: str, model_id: str | None = None, revision: str | None = None) -> Embedder:
    if kind == "sbert":
        return SbertEmbedder(model_id or DEFAULT_SBERT_MODEL, revision)
    if kind == "tfidf":
        return TfidfEmbedder()
    raise ValueError(f"unknown embedder {kind!r} (use 'sbert' or 'tfidf')")
