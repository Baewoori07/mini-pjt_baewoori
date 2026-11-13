"""Local BM25 retriever over data/knowledge/*.md (no external embedding service)."""
import math
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path

from ..shared import tracing


KNOWLEDGE_DIR = Path(__file__).resolve().parents[2] / "data" / "knowledge"


_WORD_RE = re.compile(r"[a-z0-9]+|[가-힣]+")


K1, B = 1.5, 0.75


def tokenize(text: str) -> list[str]:
    toks: list[str] = []
    for w in _WORD_RE.findall(text.lower()):
        if "가" <= w[0] <= "힣":
            toks += [w] if len(w) == 1 else [w[i:i + 2] for i in range(len(w) - 1)]
        else:
            toks.append(w)
    return toks


def load_chunks(directory: Path = KNOWLEDGE_DIR) -> list[dict]:
    """One chunk per '## ' section; the doc title is indexed with every chunk."""
    chunks = []
    for path in sorted(Path(directory).glob("*.md")):
        text = path.read_text(encoding="utf-8")
        title = path.stem
        m = re.match(r"#\s+(.+)", text)
        if m:
            title = m.group(1).strip()
        for part in re.split(r"(?m)^## ", text)[1:] or [text]:
            chunks.append({"doc_id": path.stem, "title": title, "text": part.strip()})
    return chunks


class BM25Index:
    def __init__(self, chunks: list[dict]):
        self.chunks = chunks
        self.tf = [Counter(tokenize(c["title"] + " " + c["text"])) for c in chunks]
        self.len = [sum(t.values()) for t in self.tf]
        self.avg = (sum(self.len) / len(chunks)) if chunks else 0.0
        df = Counter(t for tf in self.tf for t in tf)
        n = len(chunks)
        self.idf = {t: math.log(1 + (n - d + 0.5) / (d + 0.5)) for t, d in df.items()}

    def score(self, i: int, terms: list[str]) -> float:
        s = 0.0
        for t in terms:
            f = self.tf[i].get(t, 0)
            if f:
                s += self.idf[t] * f * (K1 + 1) / (f + K1 * (1 - B + B * self.len[i] / self.avg))
        return s

    def search(self, query: str, k: int = 3) -> list[dict]:
        terms = tokenize(query)
        scored = sorted(((self.score(i, terms), i) for i in range(len(self.chunks))), reverse=True)
        hits, seen = [], set()
        for s, i in scored:
            c = self.chunks[i]
            if s <= 0 or c["doc_id"] in seen:
                continue
            seen.add(c["doc_id"])
            hits.append({**c, "score": round(s, 4)})
            if len(hits) == k:
                break
        return hits


@lru_cache(maxsize=1)
def _default_index() -> BM25Index:
    return BM25Index(load_chunks())


def search_knowledge(query: str, k: int = 3) -> list[dict]:
    """Top-k chunks (distinct docs) with doc_id, title, text and BM25 score."""
    hits = _default_index().search(query, k)
    tracing.record_chunks([h["doc_id"] for h in hits])
    return hits
