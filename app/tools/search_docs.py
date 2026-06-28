"""
search_docs.py — LangChain tool wrapper for ChromaDB document search.

Decorated with @tool so it can be used by any LangChain agent or
directly in LangGraph nodes.
"""

from langchain_core.tools import tool

from app.rag.retriever import search_docs as _search_docs
from app.services.config import TOP_K_RETRIEVAL


@tool
def search_telecom_docs(query: str) -> str:
    """Search the telecom knowledge base for relevant 3GPP / telecom documents.

    Use this tool to find specific technical information about 5G NR, LTE,
    network slicing, HARQ, QoS, security, handover, or any other telecom topic.

    Args:
        query: A natural-language search query.

    Returns:
        A formatted string listing the most relevant document excerpts,
        including their source identifiers and similarity scores.
    """
    docs = _search_docs(query, top_k=TOP_K_RETRIEVAL)

    if not docs:
        return (
            "No relevant documents found in the knowledge base. "
            "Make sure ingestion has been run: python -m app.rag.ingest_tspec"
        )

    lines = [f"Found {len(docs)} relevant document(s):\n"]
    for i, doc in enumerate(docs, start=1):
        lines.append(
            f"[{i}] Source: {doc['source']} | Score: {doc['score']:.3f}\n"
            f"     {doc['text'][:400].replace(chr(10), ' ')}\n"
        )

    return "\n".join(lines)
