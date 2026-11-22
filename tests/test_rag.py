"""
tests/test_rag.py — NetCare AI
Unit tests for Retrieval-Augmented Generation (corpus ingestion, semantic similarity, context retrieval).
"""

import os
import sys
import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from rag.retrieval import retrieve_relevant_knowledge, initialize_rag


def test_rag_retrieval_dns():
    """Verify factual retrieval for DNS query."""
    initialize_rag()
    results = retrieve_relevant_knowledge("DNS resolution failed flush cache", top_k=2)
    assert len(results) > 0
    assert any("dns" in r["category"].lower() or "dns" in r["text"].lower() for r in results)
    assert "source" in results[0]


def test_rag_retrieval_dhcp():
    """Verify factual retrieval for DHCP APIPA 169.254 query."""
    results = retrieve_relevant_knowledge("169.254 APIPA IP address conflict lease", top_k=2)
    assert len(results) > 0
    assert any("dhcp" in r["text"].lower() or "ip" in r["text"].lower() for r in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
