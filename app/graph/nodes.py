"""
nodes.py — all agent nodes used in the LangGraph workflow.

Each function has the signature  (state: TelecomState) -> dict
and returns ONLY the fields it changes.  LangGraph merges the dict
into the running state automatically.

Nodes:
  retrieval_agent     — dense search in ChromaDB
  answer_generator    — LLM answer using retrieved context + memory
  summarization_agent — retrieve + summarise a topic
  validation_agent    — confidence scoring; flags for human approval
  human_approval_node — marks answer as pending human review
"""

import re
from typing import Dict, List

from app.graph.state import TelecomState
from app.rag.retriever import search_docs
from app.services.config import (
    CONFIDENCE_THRESHOLD,
    TOP_K_RETRIEVAL,
    TOP_K_SUMMARIZE,
)
from app.services.llm_factory import get_llm
from app.services.prompts import ANSWER_PROMPT, SUMMARIZE_PROMPT, VALIDATION_PROMPT
from app.utils.logger import setup_logger
from app.utils.retry import with_retry

log = setup_logger("nodes")


# ═══════════════════════════════════════════════════════════════════════════════
# Retrieval Agent
# ═══════════════════════════════════════════════════════════════════════════════

def retrieval_agent(state: TelecomState) -> dict:
    """Search ChromaDB for documents relevant to the user query.

    Populates: retrieved_docs
    """
    query = state["query"]
    log.info(f"[Retrieval Agent] Query: '{query[:70]}...'")

    try:
        docs = search_docs(query, top_k=TOP_K_RETRIEVAL)
        log.info(f"[Retrieval Agent] Retrieved {len(docs)} documents")
    except Exception as exc:
        log.error(f"[Retrieval Agent] Search failed: {exc}")
        docs = []

    return {"retrieved_docs": docs}


# ═══════════════════════════════════════════════════════════════════════════════
# Answer Generator
# ═══════════════════════════════════════════════════════════════════════════════

def _build_context(docs: List[Dict]) -> str:
    """Format retrieved docs into a labelled context string."""
    if not docs:
        return "No relevant documents found in the knowledge base."
    return "\n\n".join(
        f"[Source {i + 1}: {doc.get('source', 'Unknown')} | score={doc.get('score', 0):.2f}]\n{doc.get('text', '')}"
        for i, doc in enumerate(docs)
    )


def _build_history_str(history: List[Dict]) -> str:
    """Format the last 3 conversation turns as a readable string."""
    recent = history[-6:]  # last 3 user + 3 assistant messages
    if not recent:
        return "No previous conversation."
    lines = []
    for msg in recent:
        role = "User" if msg["role"] == "user" else "Assistant"
        lines.append(f"{role}: {msg['content'][:300]}")
    return "\n".join(lines)


@with_retry(max_attempts=3, wait_min=1, wait_max=8)
def _call_llm_for_answer(prompt: str) -> str:
    llm = get_llm()
    return llm.invoke(prompt).content.strip()


def answer_generator(state: TelecomState) -> dict:
    """Generate a grounded answer using retrieved context and conversation history.

    Populates: answer, sources
    """
    log.info("[Answer Generator] Generating answer...")

    docs = state.get("retrieved_docs", [])
    context = _build_context(docs)
    history_str = _build_history_str(state.get("history", []))

    prompt = ANSWER_PROMPT.format(
        context=context,
        history=history_str,
        query=state["query"],
    )

    try:
        answer = _call_llm_for_answer(prompt)
    except Exception as exc:
        log.error(f"[Answer Generator] LLM call failed after retries: {exc}")
        answer = (
            "I was unable to generate an answer due to a technical error. "
            "Please try again or rephrase your question."
        )

    sources = [
        doc.get("source", f"Document {i + 1}") for i, doc in enumerate(docs)
    ]

    log.info(f"[Answer Generator] Answer length: {len(answer)} chars")
    return {"answer": answer, "sources": sources}


# ═══════════════════════════════════════════════════════════════════════════════
# Summarization Agent
# ═══════════════════════════════════════════════════════════════════════════════

@with_retry(max_attempts=3, wait_min=1, wait_max=8)
def _call_llm_for_summary(prompt: str) -> str:
    llm = get_llm()
    return llm.invoke(prompt).content.strip()


def summarization_agent(state: TelecomState) -> dict:
    """Retrieve relevant docs and produce a structured topic summary.

    This node handles both retrieval and generation for summarisation tasks,
    avoiding a separate retrieval step when more documents are needed.

    Populates: retrieved_docs, answer, sources
    """
    query = state["query"]
    log.info(f"[Summarization Agent] Topic: '{query[:70]}...'")

    # Retrieve more docs than QA (summarisation benefits from wider context)
    try:
        docs = search_docs(query, top_k=TOP_K_SUMMARIZE)
    except Exception as exc:
        log.error(f"[Summarization Agent] Retrieval failed: {exc}")
        docs = []

    if docs:
        context = "\n\n".join(
            f"[Doc {i + 1}]\n{doc.get('text', '')}" for i, doc in enumerate(docs)
        )
    else:
        context = "No documents available. Summarise based on general knowledge."

    prompt = SUMMARIZE_PROMPT.format(query=query, context=context)

    try:
        summary = _call_llm_for_summary(prompt)
    except Exception as exc:
        log.error(f"[Summarization Agent] LLM call failed: {exc}")
        summary = "Summarisation failed due to a technical error. Please try again."

    sources = [doc.get("source", f"Doc {i + 1}") for i, doc in enumerate(docs)]

    log.info(f"[Summarization Agent] Summary length: {len(summary)} chars")
    return {"retrieved_docs": docs, "answer": summary, "sources": sources}


# ═══════════════════════════════════════════════════════════════════════════════
# Validation Agent
# ═══════════════════════════════════════════════════════════════════════════════

_CONFIDENCE_RE = re.compile(r"CONFIDENCE:\s*([\d.]+)", re.IGNORECASE)


@with_retry(max_attempts=2, wait_min=1, wait_max=5)
def _call_llm_for_validation(prompt: str) -> str:
    llm = get_llm()
    return llm.invoke(prompt).content.strip()


def validation_agent(state: TelecomState) -> dict:
    """Score the generated answer and flag for human review if confidence is low.

    Populates: confidence, needs_human_approval
    """
    query = state.get("query", "")
    answer = state.get("answer", "")
    docs = state.get("retrieved_docs", [])

    # Average retrieval score used as a quality signal independent of the LLM
    avg_retrieval_score = (
        sum(d.get("score", 0.5) for d in docs) / len(docs) if docs else 0.5
    )

    # Use top-3 docs with fuller text for better validation coverage
    context = "\n\n".join(doc.get("text", "")[:500] for doc in docs[:3])
    if not context:
        context = "No context available."

    prompt = VALIDATION_PROMPT.format(
        query=query, answer=answer, context=context
    )

    # Optimistic default — if the LLM call fails, trust the retrieval quality
    confidence = round(max(0.60, min(0.85, avg_retrieval_score)), 3)
    try:
        response_text = _call_llm_for_validation(prompt)
        match = _CONFIDENCE_RE.search(response_text)
        if match:
            llm_score = max(0.0, min(1.0, float(match.group(1))))
            # Blend: 70 % LLM judgment + 30 % retrieval quality
            confidence = round(0.70 * llm_score + 0.30 * avg_retrieval_score, 3)
        else:
            # Fallback: retrieval-based score clamped to a reasonable range
            confidence = round(max(0.55, min(0.85, avg_retrieval_score)), 3)
            log.warning(
                f"[Validation Agent] Could not parse CONFIDENCE from response; "
                f"using retrieval-based score: {confidence:.3f}"
            )
    except Exception as exc:
        confidence = round(max(0.55, min(0.85, avg_retrieval_score)), 3)
        log.warning(
            f"[Validation Agent] LLM scoring failed ({exc}); "
            f"using retrieval-based confidence: {confidence:.3f}"
        )

    needs_approval = confidence < CONFIDENCE_THRESHOLD
    status = "PASS" if not needs_approval else "NEEDS APPROVAL"
    log.info(
        f"[Validation Agent] Confidence: {confidence:.2f} → {status}"
        f" (threshold: {CONFIDENCE_THRESHOLD})"
    )

    return {"confidence": confidence, "needs_human_approval": needs_approval}


# ═══════════════════════════════════════════════════════════════════════════════
# Human Approval Node
# ═══════════════════════════════════════════════════════════════════════════════

def human_approval_node(state: TelecomState) -> dict:
    """Mark the answer as pending human approval.

    In a production system with LangGraph's interrupt support, this node
    would pause graph execution until a human submits their decision via the
    /approve endpoint.  In this MVP the graph completes immediately and the
    FastAPI layer handles the asynchronous approval flow.

    Populates: needs_human_approval (confirms True)
    """
    log.info(
        f"[Human Approval Node] Answer flagged. "
        f"Confidence={state.get('confidence', 0):.2f} < {CONFIDENCE_THRESHOLD}. "
        "Awaiting human decision via POST /approve."
    )
    return {"needs_human_approval": True}


# ═══════════════════════════════════════════════════════════════════════════════
# Conditional Edge Functions
# ═══════════════════════════════════════════════════════════════════════════════

def validation_decision(state: TelecomState) -> str:
    """Return 'needs_approval' or 'pass' for the conditional edge after validation."""
    if state.get("needs_human_approval", False):
        return "needs_approval"
    return "pass"
