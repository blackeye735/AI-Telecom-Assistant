"""
embeddings.py — embedding model factory.

Supports two backends:
  - "local"  → sentence-transformers/all-MiniLM-L6-v2 (runs on CPU, no API key)
  - "openai" → OpenAI text-embedding-3-small (requires OPENAI_API_KEY)

The model is cached with lru_cache so it is loaded only once per process.
"""

from functools import lru_cache
from typing import Any

from app.services.config import EMBEDDING_BACKEND, OPENAI_API_KEY
from app.utils.logger import setup_logger

log = setup_logger("embeddings")


@lru_cache(maxsize=1)
def get_embeddings() -> Any:
    """Return a cached LangChain embeddings object.

    Returns:
        A LangChain embeddings instance with .embed_documents() and
        .embed_query() methods.
    """
    if EMBEDDING_BACKEND == "openai":
        if not OPENAI_API_KEY:
            raise ValueError(
                "EMBEDDING_BACKEND=openai requires OPENAI_API_KEY in .env"
            )
        from langchain_openai import OpenAIEmbeddings

        log.info("Embeddings → OpenAI / text-embedding-3-small")
        return OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=OPENAI_API_KEY,
        )

    # Default: local sentence-transformers (all-MiniLM-L6-v2, ~80 MB download)
    try:
        from langchain_huggingface import HuggingFaceEmbeddings
    except ImportError:
        # Fallback for older langchain-community versions
        from langchain_community.embeddings import HuggingFaceEmbeddings  # type: ignore

    model_name = "all-MiniLM-L6-v2"
    log.info(f"Embeddings → local HuggingFace / {model_name}")
    return HuggingFaceEmbeddings(
        model_name=model_name,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
