"""Submission entry point (spec 4-1: src/retriever.py). Implementation: ``src/knowledge/``."""
from .knowledge import (KNOWLEDGE_DIR, BM25Index, format_context, load_chunks,  # noqa: F401
                        search_knowledge, sources_line, tokenize)
