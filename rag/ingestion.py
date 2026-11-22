"""
rag/ingestion.py — NetCare AI
Ingests and chunks verified technical documents from rag/documents/
"""

import os
import glob
from rag.embeddings import DocumentEmbedder

RAG_DOCS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "documents")


def parse_document(filepath: str) -> dict:
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()

    title, section, category, source = "Networking Document", "General", "general", "Internal"
    content = text

    lines = text.split("\n")
    body_lines = []
    for line in lines:
        if line.startswith("Title:"):
            title = line.replace("Title:", "").strip()
        elif line.startswith("Section:"):
            section = line.replace("Section:", "").strip()
        elif line.startswith("Category:"):
            category = line.replace("Category:", "").strip()
        elif line.startswith("Source:"):
            source = line.replace("Source:", "").strip()
        else:
            body_lines.append(line)

    content = "\n".join(body_lines).strip()
    return {
        "title": title,
        "section": section,
        "category": category,
        "source": source,
        "content": content,
        "filepath": filepath
    }


def chunk_document(doc: dict, chunk_size: int = 350, overlap: int = 50) -> list:
    words = doc["content"].split()
    chunks = []
    start = 0

    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk_text = " ".join(words[start:end])
        chunks.append({
            "title": doc["title"],
            "section": doc["section"],
            "category": doc["category"],
            "source": doc["source"],
            "text": chunk_text
        })
        if end >= len(words):
            break
        start += chunk_size - overlap

    return chunks


def load_and_index_corpus():
    files = glob.glob(os.path.join(RAG_DOCS_DIR, "*.txt"))
    all_chunks = []
    for f in files:
        doc = parse_document(f)
        chunks = chunk_document(doc)
        all_chunks.extend(chunks)

    embedder = DocumentEmbedder()
    chunk_texts = [c["text"] for c in all_chunks]
    if chunk_texts:
        matrix = embedder.fit_transform(chunk_texts)
    else:
        matrix = None

    return all_chunks, matrix, embedder
