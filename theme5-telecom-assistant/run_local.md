# Local Run Guide — Telecom Knowledge Assistant

Complete step-by-step instructions to run the project on your local machine.

---

## Prerequisites

- Python 3.10 or 3.11 (recommended)
- Git
- An Anthropic API key **OR** an OpenAI API key
- ~2 GB disk space (for PyTorch CPU + models)
- Internet access (for first-time model + dataset download)

---

## Step 1 — Create a Virtual Environment

```bash
# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1

# Mac / Linux
python -m venv .venv
source .venv/bin/activate
```

You should see `(.venv)` in your prompt.

---

## Step 2 — Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

> **Note:** `sentence-transformers` installs PyTorch CPU (~200 MB).
> For a lighter install (no PyTorch), set `EMBEDDING_BACKEND=openai` in `.env`
> and skip `sentence-transformers`:
> ```bash
> pip install -r requirements.txt --no-deps sentence-transformers
> pip install -r requirements.txt
> ```

---

## Step 3 — Configure Environment

```bash
# Windows
copy .env.example .env

# Mac / Linux
cp .env.example .env
```

Edit `.env` with your preferred text editor:

```env
# Choose your LLM provider
LLM_PROVIDER=anthropic

# Add your API key
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxxxxx

# Or use OpenAI
# LLM_PROVIDER=openai
# OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
```

Leave all other settings at their defaults for local dev.

---

## Step 4 — Ingest Telecom Documents

This downloads the TSpec-LLM dataset from HuggingFace, chunks the text,
and stores embeddings in ChromaDB.

```bash
# From the project root (theme5-telecom-assistant/)
python -m app.rag.ingest_tspec
```

Expected output:
```
2024-01-01 10:00:00 | INFO     | ingest | Loading dataset: rasoul-nikbakht/TSpec-LLM
2024-01-01 10:00:05 | INFO     | ingest | Loaded 'train' split: XXXX records
2024-01-01 10:00:05 | INFO     | ingest | Extracting 200 records from XXXX total
2024-01-01 10:00:10 | INFO     | ingest | Chunked 200 documents → XXX chunks
2024-01-01 10:00:15 | INFO     | ingest | Ingestion Complete: XXX chunks stored
```

> If HuggingFace is unavailable, use the built-in mock data:
> ```bash
> python -m app.rag.ingest_tspec --mock
> ```

---

## Step 5 — Launch FastAPI Backend

Open a terminal (keep it running):

```bash
uvicorn app.api.main:app --host 127.0.0.1 --port 8000 --reload
```

Verify the API is running:
- Health check: http://127.0.0.1:8000/health
- API docs: http://127.0.0.1:8000/docs

---

## Step 6 — Launch Streamlit UI

Open a **second terminal**, activate the venv again:

```bash
# Windows
.venv\Scripts\Activate.ps1

# Mac / Linux
source .venv/bin/activate

# Launch UI
streamlit run app/ui/streamlit_app.py
```

Streamlit will open at: http://localhost:8501

---

## Step 7 — Test Sample Queries

### Via Streamlit UI
Click any sidebar button or type directly in the chat:

- "What is 5G NR?"
- "Explain the 5G core network architecture"
- "How does HARQ work in 5G?"
- "Summarize network slicing"
- "What are 5QI values?"

### Via API (curl / httpie)

```bash
# Q&A query
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "What is 5G NR?", "session_id": "test-001"}'

# Check history
curl http://127.0.0.1:8000/history/test-001

# Approve a low-confidence answer
curl -X POST http://127.0.0.1:8000/approve \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test-001", "approved": true}'
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError` | Ensure venv is activated and `pip install -r requirements.txt` ran |
| `ANTHROPIC_API_KEY not set` | Check your `.env` file has the correct key |
| `Cannot connect to FastAPI` | Make sure `uvicorn` is running on port 8000 |
| `ChromaDB collection is empty` | Run `python -m app.rag.ingest_tspec` first |
| `HuggingFace download failed` | Run with `--mock` flag or check internet connection |
| Slow first query | Embedding model downloads on first use (~80 MB) |

---

## Directory After Setup

```
theme5-telecom-assistant/
├── chroma_db/          ← ChromaDB files (created by ingestion)
├── data/
│   ├── raw/
│   │   └── tspec_sample.json   ← sample of ingested records
│   └── processed/
│       └── chunks.json         ← preview of text chunks
```

---

## Cleaning Up

```bash
# Remove ChromaDB (re-run ingestion to rebuild)
rm -rf chroma_db/

# Remove venv
rm -rf .venv/
```
