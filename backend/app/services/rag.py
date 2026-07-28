"""Small local RAG pipeline over the knowledge base.

Documents in backend/knowledge/ (resume-writing guides + sample job
descriptions) are chunked and embedded with a lightweight local TF-IDF
embedder, then retrieved by cosine similarity.

The embedder sits behind an `Embedder` protocol so it can be swapped for a
hosted embedding model (e.g. Voyage) without touching the retrieval code —
TF-IDF keeps the demo dependency-free and fully offline.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

_TOKEN_RE = re.compile(r"[a-z0-9+#.]{2,}")

_STOPWORDS = frozenset(
    """a an and are as at be by for from has have if in into is it its of on or
    that the their there these this to was were will with you your our not can
    do does but they them then than when what which who how all any each""".split()
)


def tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS]


class Embedder(Protocol):
    """Pluggable embedding interface. Swap TfidfEmbedder for a hosted model."""

    def fit(self, corpus: list[str]) -> None: ...
    def embed(self, text: str) -> dict[str, float]: ...


class TfidfEmbedder:
    """Sparse TF-IDF vectors with pure-Python cosine similarity."""

    def __init__(self) -> None:
        self._idf: dict[str, float] = {}

    def fit(self, corpus: list[str]) -> None:
        n_docs = len(corpus)
        df: Counter[str] = Counter()
        for doc in corpus:
            df.update(set(tokenize(doc)))
        self._idf = {
            term: math.log((1 + n_docs) / (1 + count)) + 1.0 for term, count in df.items()
        }

    def embed(self, text: str) -> dict[str, float]:
        counts = Counter(tokenize(text))
        total = sum(counts.values()) or 1
        vec = {
            term: (count / total) * self._idf.get(term, 1.0)
            for term, count in counts.items()
        }
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        return {term: v / norm for term, v in vec.items()}


def cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if len(b) < len(a):
        a, b = b, a
    return sum(v * b.get(k, 0.0) for k, v in a.items())


@dataclass
class Chunk:
    doc_id: str
    title: str
    text: str
    vector: dict[str, float] = field(default_factory=dict, repr=False)


def chunk_markdown(doc_id: str, text: str, max_chars: int = 900) -> list[Chunk]:
    """Split a markdown doc on headings, then pack paragraphs into chunks."""
    title = doc_id
    first_line = text.strip().splitlines()[0] if text.strip() else ""
    if first_line.startswith("#"):
        title = first_line.lstrip("# ").strip()

    sections = re.split(r"\n(?=#{1,3} )", text)
    chunks: list[Chunk] = []
    for section in sections:
        section = section.strip()
        if not section:
            continue
        if len(section) <= max_chars:
            chunks.append(Chunk(doc_id=doc_id, title=title, text=section))
            continue
        buf = ""
        for para in section.split("\n\n"):
            if len(buf) + len(para) > max_chars and buf:
                chunks.append(Chunk(doc_id=doc_id, title=title, text=buf.strip()))
                buf = ""
            buf += para + "\n\n"
        if buf.strip():
            chunks.append(Chunk(doc_id=doc_id, title=title, text=buf.strip()))
    return chunks


class KnowledgeBase:
    """Indexes the knowledge directory and answers similarity queries."""

    def __init__(self, root: Path, embedder: Embedder | None = None) -> None:
        self.root = root
        self.embedder: Embedder = embedder or TfidfEmbedder()
        self.chunks: list[Chunk] = []
        self._build()

    def _build(self) -> None:
        docs: list[tuple[str, str]] = []
        if self.root.exists():
            for path in sorted(self.root.rglob("*.md")):
                rel = path.relative_to(self.root).as_posix()
                docs.append((rel, path.read_text(encoding="utf-8")))
        for doc_id, text in docs:
            self.chunks.extend(chunk_markdown(doc_id, text))
        self.embedder.fit([c.text for c in self.chunks] or [""])
        for chunk in self.chunks:
            chunk.vector = self.embedder.embed(f"{chunk.title}\n{chunk.text}")

    def search(self, query: str, top_k: int = 4) -> list[tuple[Chunk, float]]:
        qvec = self.embedder.embed(query)
        scored = [(chunk, cosine(qvec, chunk.vector)) for chunk in self.chunks]
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return [(c, s) for c, s in scored[:top_k] if s > 0.0]


_kb: KnowledgeBase | None = None


def get_knowledge_base() -> KnowledgeBase:
    global _kb
    if _kb is None:
        from ..config import KNOWLEDGE_DIR

        _kb = KnowledgeBase(KNOWLEDGE_DIR)
    return _kb
