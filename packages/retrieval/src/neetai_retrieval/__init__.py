"""Retrieval-Augmented Generation pipeline.

Phase 4 will add:
    * `chunking.py`   — semantic chunker
    * `embedding.py`  — batched embedding driver
    * `search.py`     — hybrid (dense + lexical) search through VectorStore
    * `rerank.py`     — cross-encoder reranker
    * `ingest.py`     — document ingestion worker entry point
"""

__version__ = "0.1.0"
