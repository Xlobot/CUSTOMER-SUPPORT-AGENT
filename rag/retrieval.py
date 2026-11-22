"""
rag/retrieval.py — NetCare AI
Retrieves factual technical context for agent queries to prevent hallucinations.
"""

import time
from rag.ingestion import load_and_index_corpus
from monitoring.temporary_logs import log_event

_INDEXED_CHUNKS = None
_DOC_MATRIX = None
_EMBEDDER = None


def initialize_rag():
    global _INDEXED_CHUNKS, _DOC_MATRIX, _EMBEDDER
    if _INDEXED_CHUNKS is None:
        _INDEXED_CHUNKS, _DOC_MATRIX, _EMBEDDER = load_and_index_corpus()


def retrieve_relevant_knowledge(query: str, top_k: int = 2) -> list:
    """Retrieves top_k relevant passages from the verified technical knowledge base."""
    start_time = time.time()
    initialize_rag()

    if not _INDEXED_CHUNKS or _DOC_MATRIX is None:
        return []

    query_vec = _EMBEDDER.transform([query])
    scores = _EMBEDDER.compute_similarity(query_vec, _DOC_MATRIX)

    # Sort by score descending
    ranked_indices = scores.argsort()[::-1][:top_k]
    results = []

    for idx in ranked_indices:
        score = float(scores[idx])
        if score > 0.05:  # Relevance threshold
            chunk = _INDEXED_CHUNKS[idx]
            results.append({
                "title": chunk["title"],
                "section": chunk["section"],
                "category": chunk["category"],
                "source": chunk["source"],
                "text": chunk["text"],
                "similarity_score": round(score, 4)
            })

    latency_ms = round((time.time() - start_time) * 1000, 2)
    log_event("INFO", "RAG Knowledge Base", f"Retrieved {len(results)} context chunks for query: '{query[:40]}...'", latency_ms=latency_ms)
    return results
