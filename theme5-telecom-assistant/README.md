# 📡 Telecom Knowledge Assistant — Theme 5

An AI-powered Q&A and summarization system for 3GPP/telecom engineering manuals.
Built as a fully local-first MVP using **LangGraph**, **ChromaDB**, **FastAPI**, and **Streamlit**.

---

## Architecture

```
User (Streamlit UI)
        │
        ▼
FastAPI Backend  ◄──► Session Memory
        │
        ▼
 LangGraph Graph
        │
   ┌────┴────┐
[Router Node]   ← classifies intent: "qa" | "summarize"
   │         │
[Retrieval  [Summarization
  Agent]      Agent]
   │              │
[Answer          │
 Generator]       │
   └──────┬───────┘
    [Validation Agent]  ← scores confidence (0–1)
          │
    ┌─────┴──────┐
  [pass]  [needs_approval]
    │            │
   END    [Human Approval Node]
                 │
                END
```

**Agents:**
| Agent | Role |
|---|---|
| Router | LLM-based intent classification (qa vs summarize) |
| Retrieval Agent | Searches ChromaDB with dense embeddings |
| Answer Generator | Claude/GPT answers using retrieved context + memory |
| Summarization Agent | Retrieves + summarizes topic documents |
| Validation Agent | Self-scores confidence; triggers human approval |
| Human Approval Node | Flags answer for human review via UI |

---

## Stack

| Layer | Technology |
|---|---|
| Agent Framework | LangGraph 0.2 |
| LLM | **OpenRouter (openai/gpt-4o)** — Unified API for 200+ models |
| LLM Alternatives | Anthropic Claude, OpenAI GPT, GitHub Models, Ollama |
| Embeddings | `all-MiniLM-L6-v2` via sentence-transformers (local) |
| Vector DB | ChromaDB (local persistent) |
| RAG | LangChain |
| Backend API | FastAPI + uvicorn |
| Frontend | Streamlit |
| Dataset | `rasoul-nikbakht/TSpec-LLM` (HuggingFace) |

**🚀 NEW:** Full production deployment guide available in [PRODUCTION_GUIDE.md](PRODUCTION_GUIDE.md)

---

## Quick Start

See [run_local.md](run_local.md) for full setup instructions.

```bash
# 1. Create and activate venv
python -m venv .venv && .venv\Scripts\activate   # Windows
# python -m venv .venv && source .venv/bin/activate  # Mac/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure API keys
copy .env.example .env   # then edit .env with your key

# 4. Ingest telecom documents
python -m app.rag.ingest_tspec

# 5. Start FastAPI backend
uvicorn app.api.main:app --host 127.0.0.1 --port 8000 --reload

# 6. Start Streamlit UI (new terminal)
streamlit run app/ui/streamlit_app.py
```

---

## Project Structure

```
theme5-telecom-assistant/
├── app/
│   ├── api/            # FastAPI backend
│   ├── ui/             # Streamlit frontend
│   ├── graph/          # LangGraph nodes, router, state, graph builder
│   ├── rag/            # Ingestion, chunking, embeddings, retriever
│   ├── services/       # Config, LLM factory, prompts
│   ├── memory/         # Session conversation memory
│   ├── tools/          # LangChain tools (search, summarize, approval)
│   └── utils/          # Logger, retry decorator
├── data/
│   ├── raw/            # Downloaded dataset samples
│   ├── processed/      # Chunked documents
│   └── eval/           # Evaluation datasets (future)
├── chroma_db/          # ChromaDB persistent storage
├── requirements.txt
├── .env.example
├── README.md
└── run_local.md
```

---

## Sample Queries

**Q&A:**
- "What is 5G NR and what frequency bands does it use?"
- "Explain the 5G core network architecture and its main functions"
- "How does HARQ work in 5G NR?"
- "What are 5QI values and how are they used?"
- "Describe the difference between FR1 and FR2 in 5G"

**Summarization:**
- "Summarize network slicing in 5G"
- "Give me an overview of 3GPP release history"
- "What is Open RAN? Summarize the key components"

---

## AWS EC2 + S3 Deployment Notes

- Replace `PersistentClient(path=...)` in `vector_store.py` with a hosted vector DB (e.g., OpenSearch or hosted Chroma)
- Store documents in S3; update `ingest_tspec.py` to read from `s3://your-bucket/docs/`
- Run FastAPI behind gunicorn/nginx on EC2
- Use AWS Secrets Manager instead of `.env` for API keys
- Use DynamoDB or ElastiCache (Redis) for session memory instead of in-memory dict
- Set up an Application Load Balancer for the FastAPI service
- Deploy Streamlit on EC2 or as an Amplify app

---

## Rubric Coverage

| Feature | Implementation |
|---|---|
| RAG chatbot | ChromaDB + LangChain + LLM |
| Context-aware answers | History injected into answer prompt |
| Document summarization | Summarization Agent node |
| Retrieval Agent | Dedicated graph node |
| Answer Validation Agent | Confidence scoring node |
| Summarization Agent | Dedicated graph node |
| Memory-aware chat | SessionMemory class in FastAPI |
| Multi-agent workflow | LangGraph with 5 nodes |
| Sequential execution | retrieval → generation → validation |
| Router-based decisions | LLM intent classification |
| Human approval step | Human Approval Node + /approve endpoint |
| Tool-using agents | LangChain `@tool` decorators |
| Error handling & retries | `tenacity` retry decorator |
| Local-first + AWS-ready | Local ChromaDB, S3/DynamoDB-ready |
