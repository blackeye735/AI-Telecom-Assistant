"""
chunking.py -- text splitting utilities for telecom documents.

Uses a pure-Python recursive splitter that requires zero extra packages.
If langchain_text_splitters or langchain is installed it is used instead,
but neither is required.
"""

from typing import Any, Dict, List, Optional

from app.services.config import CHUNK_SIZE, CHUNK_OVERLAP
from app.utils.logger import setup_logger

log = setup_logger("chunking")

# Separators ordered from coarsest (paragraph) to finest (character)
_SEPARATORS = ["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " ", ""]

# Try LangChain splitter; fall back to built-in below
try:
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter as _LC
    except ImportError:
        from langchain.text_splitter import RecursiveCharacterTextSplitter as _LC  # type: ignore
    _USE_LANGCHAIN = True
except ImportError:
    _USE_LANGCHAIN = False


# -- Pure-Python splitter (no dependencies) -----------------------------------

def _split_text_pure(text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
    """Recursively split text on a priority list of separators."""

    def _split(txt: str, seps: List[str]) -> List[str]:
        if not seps or len(txt) <= chunk_size:
            return [txt] if txt.strip() else []
        sep, rest = seps[0], seps[1:]
        parts = txt.split(sep) if sep else list(txt)
        chunks: List[str] = []
        current = ""
        for part in parts:
            candidate = (current + sep + part) if current else part
            if len(candidate) <= chunk_size:
                current = candidate
            else:
                if current:
                    chunks.append(current)
                if len(part) > chunk_size:
                    chunks.extend(_split(part, rest))
                    current = ""
                else:
                    current = part
        if current:
            chunks.append(current)
        return chunks

    raw = _split(text, _SEPARATORS)
    if not raw:
        return []
    if chunk_overlap <= 0 or len(raw) <= 1:
        return [c.strip() for c in raw if c.strip()]

    # Apply overlap: prepend tail of previous chunk
    result = [raw[0]]
    for i in range(1, len(raw)):
        overlap_text = raw[i - 1][-chunk_overlap:]
        result.append((overlap_text + " " + raw[i]).strip())
    return [c for c in result if c]


def _split_text(text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
    """Dispatch to LangChain when available, otherwise pure-Python splitter."""
    if _USE_LANGCHAIN:
        splitter = _LC(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=_SEPARATORS,
            length_function=len,
        )
        return splitter.split_text(text)
    return _split_text_pure(text, chunk_size, chunk_overlap)


# -- Public API ---------------------------------------------------------------

def chunk_documents(
    documents: List[Dict[str, Any]],
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Split a list of document dicts into text chunks.

    Each input document must have:
        "text"     : str  -- raw document text
        "metadata" : dict -- key/value metadata to propagate (optional)

    Returns a list of chunk dicts with "text" and "metadata" keys.
    """
    cs = chunk_size or CHUNK_SIZE
    co = chunk_overlap or CHUNK_OVERLAP
    chunks: List[Dict[str, Any]] = []

    for doc in documents:
        text = (doc.get("text") or "").strip()
        metadata = dict(doc.get("metadata") or {})

        if len(text) < 30:
            continue  # skip near-empty documents

        split_texts = _split_text(text, cs, co)
        for i, chunk_text in enumerate(split_texts):
            chunks.append({
                "text": chunk_text,
                "metadata": {
                    **metadata,
                    "chunk_index": i,
                    "chunk_total": len(split_texts),
                },
            })

    backend = "LangChain" if _USE_LANGCHAIN else "built-in"
    log.info(f"Chunked {len(documents)} docs -> {len(chunks)} chunks (splitter: {backend})")
    return chunks
