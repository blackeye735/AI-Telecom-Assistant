"""
vector_store.py — ChromaDB client and collection management.

ChromaDB is used in persistent mode so the vector index survives restarts.
The client and collection are cached so only one connection is held per process.

For AWS deployment: swap PersistentClient for a hosted Chroma server or
replace with OpenSearch / Pinecone — the retriever interface stays the same.
"""

from functools import lru_cache
from typing import Optional

import chromadb
from chromadb.config import Settings

from app.services.config import CHROMA_DB_DIR, CHROMA_COLLECTION
from app.utils.logger import setup_logger

log = setup_logger("vector_store")


@lru_cache(maxsize=1)
def get_chroma_client() -> chromadb.PersistentClient:
    """Return a cached persistent ChromaDB client."""
    CHROMA_DB_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(
        path=str(CHROMA_DB_DIR),
        settings=Settings(anonymized_telemetry=False),
    )
    log.info(f"ChromaDB client → {CHROMA_DB_DIR}")
    return client


def get_or_create_collection(
    collection_name: Optional[str] = None,
) -> chromadb.Collection:
    """Get an existing collection or create it if it doesn't exist."""
    name = collection_name or CHROMA_COLLECTION
    client = get_chroma_client()
    collection = client.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},  # cosine similarity for normalised embeddings
    )
    log.info(f"Collection '{name}' has {collection.count()} documents")
    return collection


def collection_has_data(collection_name: Optional[str] = None) -> bool:
    """Return True if the collection exists and contains at least one document."""
    name = collection_name or CHROMA_COLLECTION
    try:
        client = get_chroma_client()
        col = client.get_collection(name)
        return col.count() > 0
    except Exception:
        return False


def delete_collection(collection_name: Optional[str] = None) -> None:
    """Delete a collection (use carefully — irreversible)."""
    name = collection_name or CHROMA_COLLECTION
    client = get_chroma_client()
    client.delete_collection(name)
    log.warning(f"Deleted collection '{name}'")
