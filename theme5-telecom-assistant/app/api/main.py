"""
main.py — FastAPI backend for the Telecom Knowledge Assistant.

Endpoints:
  GET  /health                  — liveness check
  POST /chat                    — run a query through the LangGraph pipeline
  POST /approve                 — approve or reject a low-confidence answer
  GET  /history/{session_id}    — retrieve conversation history
  DELETE /history/{session_id}  — clear conversation history

The LangGraph is compiled once at startup and reused for all requests.
Session memory is held in-process (replace with Redis/DynamoDB for AWS).
"""

import uuid
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.graph.graph_builder import build_graph
from app.graph.state import TelecomState
from app.memory.session_memory import session_memory
from app.utils.logger import setup_logger

log = setup_logger("api")

# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="Telecom Knowledge Assistant",
    description=(
        "AI-powered Q&A and summarisation over 3GPP / telecom specifications. "
        "Powered by LangGraph, ChromaDB, and Claude/GPT."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # restrict in production
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Global state ──────────────────────────────────────────────────────────────
_graph = None  # compiled LangGraph — built once on startup

# Pending approvals: {session_id: {answer, confidence, sources}}
_pending_approvals: Dict[str, Dict[str, Any]] = {}


# ── Startup ───────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup_event() -> None:
    global _graph
    log.info("Building LangGraph pipeline…")
    _graph = build_graph()
    log.info("LangGraph ready.")


# ── Request / Response models ─────────────────────────────────────────────────

class ChatRequest(BaseModel):
    query: str = Field(..., description="User's question or request")
    session_id: Optional[str] = Field(
        None, description="Session UUID; one is created if omitted"
    )


class ChatResponse(BaseModel):
    session_id: str
    intent: str
    answer: str
    confidence: float
    needs_human_approval: bool
    sources: List[str]


class ApprovalRequest(BaseModel):
    session_id: str = Field(..., description="Session that has a pending approval")
    approved: bool = Field(..., description="True = accept the draft answer, False = reject")


class ApprovalResponse(BaseModel):
    session_id: str
    approved: bool
    final_answer: str


class HistoryResponse(BaseModel):
    session_id: str
    turn_count: int
    history: List[Dict[str, str]]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_initial_state(session_id: str, query: str) -> TelecomState:
    """Build a fresh LangGraph state for a new request."""
    history = session_memory.get_history(session_id)
    return TelecomState(
        session_id=session_id,
        query=query,
        intent="",
        history=history,
        retrieved_docs=[],
        answer="",
        confidence=0.0,
        needs_human_approval=False,
        human_approved=None,
        sources=[],
        error=None,
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
async def health() -> Dict[str, Any]:
    """Liveness check."""
    return {
        "status": "ok",
        "graph_ready": _graph is not None,
        "active_sessions": session_memory.active_session_count(),
        "pending_approvals": len(_pending_approvals),
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    """Run the user's query through the LangGraph pipeline.

    - If the answer passes validation (confidence ≥ threshold), it is returned directly.
    - If the answer requires human approval, the response includes
      ``needs_human_approval=True`` and the draft answer.  The caller should
      then POST to ``/approve`` to finalise.
    """
    if _graph is None:
        raise HTTPException(status_code=503, detail="Graph not yet initialised")

    session_id = req.session_id or str(uuid.uuid4())
    initial_state = _make_initial_state(session_id, req.query)

    log.info(f"[/chat] session={session_id} query='{req.query[:80]}'")

    try:
        result: TelecomState = _graph.invoke(initial_state)
    except Exception as exc:
        log.error(f"[/chat] Graph execution error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Pipeline error: {exc}")

    answer = result.get("answer") or "I could not generate an answer."
    confidence = result.get("confidence", 0.0)
    needs_approval = result.get("needs_human_approval", False)
    sources = result.get("sources", [])
    intent = result.get("intent", "qa")

    # Persist this turn in session memory regardless of approval status
    session_memory.add_turn(session_id, req.query, answer)

    # Store draft in the pending-approval cache if a human must review it
    if needs_approval:
        _pending_approvals[session_id] = {
            "answer": answer,
            "confidence": confidence,
            "sources": sources,
        }
        log.info(f"[/chat] Stored pending approval for session {session_id}")

    return ChatResponse(
        session_id=session_id,
        intent=intent,
        answer=answer,
        confidence=round(confidence, 3),
        needs_human_approval=needs_approval,
        sources=sources,
    )


@app.post("/approve", response_model=ApprovalResponse)
async def approve(req: ApprovalRequest) -> ApprovalResponse:
    """Accept or reject a draft answer that was flagged for human approval.

    - approved=True  → return the draft answer as final.
    - approved=False → return a message asking the user to rephrase.
    """
    pending = _pending_approvals.pop(req.session_id, None)
    if pending is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No pending approval found for session '{req.session_id}'. "
                "The session may have already been resolved or expired."
            ),
        )

    if req.approved:
        final_answer = pending["answer"]
        log.info(f"[/approve] Approved — session={req.session_id}")
    else:
        final_answer = (
            "The answer was not approved by the human reviewer. "
            "Please rephrase your question or provide more context for a better response."
        )
        log.info(f"[/approve] Rejected — session={req.session_id}")

    return ApprovalResponse(
        session_id=req.session_id,
        approved=req.approved,
        final_answer=final_answer,
    )


@app.get("/history/{session_id}", response_model=HistoryResponse)
async def get_history(session_id: str) -> HistoryResponse:
    """Return the conversation history for a session."""
    history = session_memory.get_history(session_id)
    info = session_memory.get_info(session_id)
    return HistoryResponse(
        session_id=session_id,
        turn_count=info["turn_count"],
        history=history,
    )


@app.delete("/history/{session_id}")
async def clear_history(session_id: str) -> Dict[str, str]:
    """Clear the conversation history for a session."""
    session_memory.clear_session(session_id)
    _pending_approvals.pop(session_id, None)
    return {"status": "cleared", "session_id": session_id}
