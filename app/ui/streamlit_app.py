"""
streamlit_app.py — Streamlit frontend for the Telecom Knowledge Assistant.

Run with:
    streamlit run app/ui/streamlit_app.py

The UI calls the FastAPI backend over HTTP (httpx).  Make sure the backend
is running first:
    uvicorn app.api.main:app --host 127.0.0.1 --port 8000 --reload
"""

import uuid

import httpx
import streamlit as st

# ── Page configuration ────────────────────────────────────────────────────────
st.set_page_config(
    page_title="📡 Telecom Knowledge Assistant",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Determine API base URL ────────────────────────────────────────────────────
# Allow override via st.secrets or environment so it works after deployment
try:
    API_BASE = st.secrets.get("API_BASE_URL", "http://127.0.0.1:8000")
except Exception:
    API_BASE = "http://127.0.0.1:8000"

_TIMEOUT = 90.0  # seconds per API call


# ── Session state initialisation ──────────────────────────────────────────────
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    # Each entry: {role, content, confidence, sources, intent, needs_review, reviewed}
    st.session_state.messages = []


# ── API helpers ───────────────────────────────────────────────────────────────

def api_post(endpoint: str, payload: dict) -> dict | None:
    """POST to FastAPI and return parsed JSON, or None on error."""
    url = f"{API_BASE}{endpoint}"
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            return resp.json()
    except httpx.ConnectError:
        st.error(
            "⛔ Cannot reach the FastAPI backend.  "
            "Start it in a separate terminal:  \n"
            "```\nuvicorn app.api.main:app --host 127.0.0.1 --port 8000 --reload\n```"
        )
    except httpx.HTTPStatusError as exc:
        st.error(f"API error {exc.response.status_code}: {exc.response.text[:200]}")
    except Exception as exc:
        st.error(f"Unexpected error: {exc}")
    return None


def api_delete(endpoint: str) -> None:
    """DELETE request to FastAPI (fire-and-forget)."""
    try:
        with httpx.Client(timeout=10.0) as client:
            client.delete(f"{API_BASE}{endpoint}")
    except Exception:
        pass


# ── UI helpers ────────────────────────────────────────────────────────────────

def confidence_label(score: float) -> str:
    """Human-readable confidence badge."""
    if score >= 0.75:
        return f"🟢 High confidence ({score:.0%})"
    elif score >= 0.55:
        return f"🟡 Medium confidence ({score:.0%})"
    else:
        return f"🔴 Low confidence ({score:.0%}) — review suggested"


def render_sources(sources: list[str]) -> None:
    """Render source document chips in an expander."""
    if not sources:
        return
    with st.expander(f"📚 {len(sources)} source document(s)", expanded=False):
        for i, src in enumerate(sources, start=1):
            st.markdown(f"**[{i}]** `{src}`")


def render_message(msg: dict, msg_idx: int = -1) -> None:
    """Display a chat message with confidence badge, sources, and optional inline review."""
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant":
            intent = msg.get("intent", "qa")
            label = "📝 Summary" if intent == "summarize" else "💬 Answer"
            st.markdown(f"*{label}*\n\n{msg['content']}")
        else:
            st.markdown(msg["content"])

        if msg["role"] == "assistant" and msg.get("confidence") is not None:
            st.caption(confidence_label(msg["confidence"]))

        if msg.get("sources"):
            render_sources(msg["sources"])

        # Non-blocking inline review — shown only for low-confidence answers not yet reviewed
        if msg_idx >= 0 and msg.get("needs_review") and not msg.get("reviewed"):
            with st.expander(
                f"⚠️ Confidence {msg['confidence']:.0%} — optional human review",
                expanded=False,
            ):
                st.info(
                    "This answer scored below the confidence threshold. "
                    "It has been delivered automatically. "
                    "Approve or reject to log your decision."
                )
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(
                        "✅ Approve",
                        key=f"approve_{msg_idx}",
                        use_container_width=True,
                        type="primary",
                    ):
                        api_post(
                            "/approve",
                            {"session_id": st.session_state.session_id, "approved": True},
                        )
                        st.session_state.messages[msg_idx]["reviewed"] = True
                        st.session_state.messages[msg_idx]["needs_review"] = False
                        st.rerun()
                with col2:
                    if st.button(
                        "❌ Reject",
                        key=f"reject_{msg_idx}",
                        use_container_width=True,
                    ):
                        api_post(
                            "/approve",
                            {"session_id": st.session_state.session_id, "approved": False},
                        )
                        st.session_state.messages[msg_idx]["reviewed"] = True
                        st.session_state.messages[msg_idx]["needs_review"] = False
                        st.rerun()


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📡 Telecom Assistant")
    st.caption("AI-powered 3GPP / 5G knowledge base")
    st.divider()

    # Session info
    short_id = st.session_state.session_id[:8]
    turn_count = len([m for m in st.session_state.messages if m["role"] == "user"])
    st.markdown(f"**Session:** `{short_id}…`")
    st.metric("Turns", turn_count)

    if st.button("🔄 New Session", use_container_width=True):
        api_delete(f"/history/{st.session_state.session_id}")
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.rerun()

    st.divider()

    # Quick-launch sample questions
    st.markdown("### 💬 Sample Questions")
    samples = [
        "How does 5G NR work?",
        "Explain the 5G core network architecture",
        "How does HARQ work in 5G?",
        "What are 5QI values in 5G QoS?",
        "What is the difference between FR1 and FR2?",
        "Summarize network slicing in 5G",
        "What is Open RAN?",
        "Summarize the 3GPP release history",
        "How does 5G handover work?",
        "What is NB-IoT and how does it save battery?",
    ]
    for sample in samples:
        if st.button(sample, use_container_width=True, key=f"btn_{sample[:25]}"):
            st.session_state["_prefill"] = sample
            st.rerun()

    st.divider()
    st.markdown(
        "**Stack:** LangGraph · ChromaDB · FastAPI · Streamlit  \n"
        "**Data:** TSpec-LLM (3GPP specs)"
    )


# ── Main area ─────────────────────────────────────────────────────────────────
st.title("📡 AI-Powered Telecom Knowledge Assistant")
st.caption(
    "Ask questions about 5G NR, LTE, 3GPP standards, network slicing, HARQ, QoS, "
    "and more — or request a topic summary."
)

st.divider()

# Render existing conversation
for i, msg in enumerate(st.session_state.messages):
    render_message(msg, i)

# ── Chat input ────────────────────────────────────────────────────────────────
prefill = st.session_state.pop("_prefill", None)

user_input = st.chat_input("Ask about 5G NR, LTE, HARQ, network slicing, 3GPP specs…")

if prefill and not user_input:
    user_input = prefill

# ── Process query ─────────────────────────────────────────────────────────────
if user_input:
    # Add user message to state and render it immediately
    user_msg = {"role": "user", "content": user_input}
    st.session_state.messages.append(user_msg)

    with st.chat_message("user"):
        st.markdown(user_input)

    # Call backend and show a spinner while waiting
    with st.chat_message("assistant"):
        with st.spinner("🔍 Searching telecom knowledge base…"):
            result = api_post(
                "/chat",
                {
                    "session_id": st.session_state.session_id,
                    "query": user_input,
                },
            )

    if result:
        answer = result["answer"]
        confidence = result["confidence"]
        needs_review = result["needs_human_approval"]
        sources = result.get("sources", [])
        intent = result.get("intent", "qa")

        # Always deliver the answer — approval is non-blocking and optional
        assistant_msg = {
            "role": "assistant",
            "content": answer,
            "confidence": confidence,
            "sources": sources,
            "intent": intent,
            "needs_review": needs_review,
            "reviewed": False,
        }
        st.session_state.messages.append(assistant_msg)
        # Rerun so the message renders via the history loop with proper index
        # (needed for inline approval button keys to work correctly)
        st.rerun()
