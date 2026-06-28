"""
graph_builder.py — assembles and compiles the LangGraph state machine.

The compiled graph is a callable that accepts an initial TelecomState dict
and returns the final state after all nodes have run.

Graph topology (ASCII art):
                        ┌─────────────┐
                        │  router     │
                        └──────┬──────┘
              intent="qa"      │         intent="summarize"
             ┌─────────────────┴──────────────────┐
             ▼                                     ▼
    ┌────────────────┐                  ┌──────────────────────┐
    │ retrieval_agent│                  │ summarization_agent  │
    └───────┬────────┘                  └──────────┬───────────┘
            ▼                                      │
    ┌────────────────┐                             │
    │answer_generator│                             │
    └───────┬────────┘                             │
            └──────────────┬───────────────────────┘
                           ▼
                  ┌────────────────┐
                  │validation_agent│
                  └───────┬────────┘
            confidence≥threshold    confidence<threshold
             ┌─────────────┴──────────────────┐
             ▼                                 ▼
            END                   ┌───────────────────────┐
                                  │  human_approval_node  │
                                  └───────────┬───────────┘
                                              ▼
                                             END
"""

from langgraph.graph import END, StateGraph

from app.graph.nodes import (
    answer_generator,
    human_approval_node,
    retrieval_agent,
    summarization_agent,
    validation_agent,
    validation_decision,
)
from app.graph.router import route_decision, router_node
from app.graph.state import TelecomState
from app.utils.logger import setup_logger

log = setup_logger("graph_builder")


def build_graph():
    """Build and compile the Telecom Assistant LangGraph.

    Returns:
        A compiled LangGraph that accepts TelecomState and returns TelecomState.
    """
    graph = StateGraph(TelecomState)

    # ── Register nodes ────────────────────────────────────────────────────────
    graph.add_node("router", router_node)
    graph.add_node("retrieval_agent", retrieval_agent)
    graph.add_node("answer_generator", answer_generator)
    graph.add_node("summarization_agent", summarization_agent)
    graph.add_node("validation_agent", validation_agent)
    graph.add_node("human_approval_node", human_approval_node)

    # ── Entry point ───────────────────────────────────────────────────────────
    graph.set_entry_point("router")

    # ── Router → branch on intent ─────────────────────────────────────────────
    graph.add_conditional_edges(
        "router",
        route_decision,
        {
            "qa": "retrieval_agent",
            "summarize": "summarization_agent",
        },
    )

    # ── QA path: retrieval → answer → validation ──────────────────────────────
    graph.add_edge("retrieval_agent", "answer_generator")
    graph.add_edge("answer_generator", "validation_agent")

    # ── Summarise path: summarization → validation ────────────────────────────
    graph.add_edge("summarization_agent", "validation_agent")

    # ── Validation → pass or flag for human ──────────────────────────────────
    graph.add_conditional_edges(
        "validation_agent",
        validation_decision,
        {
            "pass": END,
            "needs_approval": "human_approval_node",
        },
    )

    # ── Human approval → end ──────────────────────────────────────────────────
    graph.add_edge("human_approval_node", END)

    compiled = graph.compile()
    log.info("LangGraph compiled successfully (6 nodes, 2 conditional branches)")
    return compiled
