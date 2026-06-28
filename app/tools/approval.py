"""
approval.py — LangChain tool for requesting human approval.

When an answer has low confidence, this tool flags it for review.
In the graph workflow, the human_approval_node handles this automatically;
this tool is provided for tool-using agent patterns.
"""

from langchain_core.tools import tool

from app.utils.logger import setup_logger

log = setup_logger("approval_tool")


@tool
def request_human_approval(answer: str, confidence: float, reason: str = "") -> str:
    """Flag a low-confidence answer for human review before delivery.

    This tool signals that the answer should not be returned to the user
    without a human checking it first.

    Args:
        answer:     The draft answer text.
        confidence: Confidence score between 0.0 and 1.0.
        reason:     Optional explanation for why confidence is low.

    Returns:
        A structured string that triggers the approval workflow.
    """
    log.info(
        f"[Approval Tool] Human review requested. "
        f"confidence={confidence:.2f}, reason={reason or 'not specified'}"
    )

    return (
        f"APPROVAL_REQUIRED\n"
        f"confidence={confidence:.2f}\n"
        f"reason={reason or 'Low confidence in generated answer'}\n"
        f"draft_answer={answer}"
    )
