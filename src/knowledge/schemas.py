"""Knowledge chunk types."""
from typing import TypedDict


class Chunk(TypedDict):
    doc_id: str      # file stem in data/knowledge
    title: str       # '# ' heading of the document
    text: str        # one '## ' section


class Hit(Chunk, total=False):
    score: float     # BM25 score
