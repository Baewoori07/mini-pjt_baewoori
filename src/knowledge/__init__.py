"""Knowledge domain (RAG): BM25 search over the swim-coaching knowledge base."""
from .prompts import format_context, sources_line
from .retriever import KNOWLEDGE_DIR, BM25Index, load_chunks, search_knowledge, tokenize
from .schemas import Chunk, Hit

__all__ = ["BM25Index", "Chunk", "Hit", "KNOWLEDGE_DIR", "format_context", "load_chunks",
           "search_knowledge", "sources_line", "tokenize"]
