"""
retriever.py — semantic document retrieval from ChromaDB.

search_docs() is the single function called by graph nodes and tools.
It returns a list of dicts so the rest of the codebase does not need
to import chromadb directly.
"""

from typing import Any, Dict, List, Optional

from app.rag.embeddings import get_embeddings
from app.rag.vector_store import get_chroma_client, collection_has_data
from app.services.config import CHROMA_COLLECTION, TOP_K_RETRIEVAL
from app.utils.logger import setup_logger

log = setup_logger("retriever")


def search_docs(
    query: str,
    top_k: Optional[int] = None,
    collection_name: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Search ChromaDB for documents semantically similar to *query*.

    Args:
        query:           User's natural-language question or topic.
        top_k:           Maximum number of documents to return.
        collection_name: ChromaDB collection to query (defaults to config value).

    Returns:
        List of dicts, each with keys:
            "text"     : str   — chunk content
            "source"   : str   — document source identifier
            "topic"    : str   — topic tag (if available)
            "score"    : float — cosine similarity score (0–1, higher is better)
            "metadata" : dict  — full metadata from ChromaDB
    """
    k = top_k or TOP_K_RETRIEVAL
    col_name = collection_name or CHROMA_COLLECTION

    if not collection_has_data(col_name):
        log.warning(
            "ChromaDB collection is empty or missing. "
            "Run: python -m app.rag.ingest_tspec"
        )
        return []

    # Embed the query
    embeddings_model = get_embeddings()
    query_vector = embeddings_model.embed_query(query)

    # Query ChromaDB
    client = get_chroma_client()
    collection = client.get_collection(col_name)
    n_results = min(k, collection.count())

    raw = collection.query(
        query_embeddings=[query_vector],
        n_results=n_results,
        include=["documents", "metadatas", "distances"],
    )

    docs: List[Dict[str, Any]] = []
    for doc_text, metadata, distance in zip(
        raw["documents"][0],
        raw["metadatas"][0],
        raw["distances"][0],
    ):
        # ChromaDB cosine distance is in [0, 2]; convert to similarity [0, 1]
        score = max(0.0, min(1.0, 1.0 - distance / 2.0))
        docs.append(
            {
                "text": doc_text,
                "source": metadata.get("source", "unknown"),
                "topic": metadata.get("topic", ""),
                "score": round(score, 4),
                "metadata": metadata,
            }
        )

    log.info(
        f"Retrieved {len(docs)} docs for query: '{query[:60]}...' "
        f"(top score: {docs[0]['score'] if docs else 'n/a'})"
    )
    return docs
