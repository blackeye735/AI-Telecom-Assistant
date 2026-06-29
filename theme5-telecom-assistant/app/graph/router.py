"""
router.py — intent-classification node for the LangGraph.

The router decides whether a query should go to the Retrieval Agent (QA)
or the Summarization Agent.  A fast keyword scan is tried first; only on
a miss does it make an LLM call to avoid unnecessary latency.
"""

from app.graph.state import TelecomState
from app.services.llm_factory import get_llm
from app.services.prompts import ROUTER_PROMPT
from app.utils.logger import setup_logger
from app.utils.retry import with_retry

log = setup_logger("router")

# Only explicit summarization requests.  Factual questions such as
# "what is X", "how does X work", "explain X" are better served by
# the QA retrieval path — do NOT list them here.
_SUMMARIZE_KEYWORDS = {
    "summarize", "summary", "summarise",
    "give me an overview", "give me a summary", "overview of",
    "introduction to", "key points about", "outline the",
    "what are the main", "what are the key",
}


@with_retry(max_attempts=2, wait_min=1, wait_max=5)
def _llm_classify(query: str) -> str:
    """Ask the LLM to classify the query as 'qa' or 'summarize'."""
    llm = get_llm()
    prompt = ROUTER_PROMPT.format(query=query)
    response = llm.invoke(prompt)
    label = response.content.strip().lower()
    return "summarize" if "summarize" in label else "qa"


def router_node(state: TelecomState) -> dict:
    """Classify the query intent and update state["intent"].

    Returns only the fields that change — LangGraph merges with existing state.
    """
    query = state["query"]
    query_lower = query.lower()

    # 1. Fast keyword check — avoids an LLM call for obvious cases
    if any(kw in query_lower for kw in _SUMMARIZE_KEYWORDS):
        intent = "summarize"
        log.info(f"Router → summarize (keyword match)")
    else:
        # 2. LLM classification for ambiguous queries
        try:
            intent = _llm_classify(query)
            log.info(f"Router → {intent} (LLM classification)")
        except Exception as exc:
            log.warning(f"Router LLM failed ({exc}); defaulting to 'qa'")
            intent = "qa"

    return {"intent": intent}


def route_decision(state: TelecomState) -> str:
    """Conditional-edge function: returns the next node name based on intent."""
    return state.get("intent", "qa")
