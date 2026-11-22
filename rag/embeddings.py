"""
rag/embeddings.py — NetCare AI
Vector embeddings and similarity metrics for RAG knowledge documents.
"""

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np


class DocumentEmbedder:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            stop_words="english",
            sublinear_tf=True
        )
        self.is_fitted = False

    def fit_transform(self, texts: list):
        vectors = self.vectorizer.fit_transform(texts)
        self.is_fitted = True
        return vectors

    def transform(self, texts: list):
        if not self.is_fitted:
            raise ValueError("Embedder has not been fitted.")
        return self.vectorizer.transform(texts)

    def compute_similarity(self, query_vec, doc_matrix):
        return cosine_similarity(query_vec, doc_matrix)[0]
