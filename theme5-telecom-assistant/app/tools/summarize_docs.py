"""
summarize_docs.py — LangChain tool for topic summarisation.

Retrieves relevant documents from ChromaDB and generates a structured
summary using the configured LLM.
"""

from langchain_core.tools import tool

from app.rag.retriever import search_docs
from app.services.config import TOP_K_SUMMARIZE
from app.services.llm_factory import get_llm
from app.services.prompts import SUMMARIZE_PROMPT
from app.utils.logger import setup_logger
from app.utils.retry import with_retry

log = setup_logger("summarize_tool")


@with_retry(max_attempts=2)
def _generate_summary(topic: str, context: str) -> str:
    llm = get_llm()
    prompt = SUMMARIZE_PROMPT.format(query=topic, context=context)
    return llm.invoke(prompt).content.strip()


@tool
def summarize_telecom_topic(topic: str) -> str:
    """Retrieve and summarise telecom documents about a specific topic.

    Use this tool when the user requests an overview, explanation, or summary
    of a 3GPP / telecom concept (e.g., 'summarise network slicing').

    Args:
        topic: The telecom topic or concept to summarise.

    Returns:
        A structured summary with key facts and takeaways.
    """
    docs = search_docs(topic, top_k=TOP_K_SUMMARIZE)

    if not docs:
        context = "No documents available. Use general knowledge about telecom standards."
        log.warning(f"No docs found for topic: {topic}")
    else:
        context = "\n\n".join(
            f"[Doc {i + 1}]\n{doc['text']}" for i, doc in enumerate(docs)
        )
        log.info(f"Summarising '{topic}' using {len(docs)} docs")

    try:
        return _generate_summary(topic, context)
    except Exception as exc:
        log.error(f"Summarisation failed: {exc}")
        return f"Summarisation failed for '{topic}'. Please try again."
