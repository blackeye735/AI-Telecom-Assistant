"""
config.py — single source of truth for all runtime settings.

Values are loaded from environment variables (or .env via python-dotenv).
No secret values are hard-coded; .env.example shows required keys.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the project root (two levels above this file)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(_PROJECT_ROOT / ".env")

# ── Project paths ─────────────────────────────────────────────────────────────
BASE_DIR = _PROJECT_ROOT
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw" / "tspec_sample"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
EVAL_DATA_DIR = DATA_DIR / "eval"
CHROMA_DB_DIR = BASE_DIR / "chroma_db"

# ── LLM provider ──────────────────────────────────────────────────────────────
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "anthropic").lower()  # "anthropic" | "openai" | "openrouter"

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-haiku-20240307")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

# OpenRouter (unified API for 200+ models)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o")

LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "1024"))

# GitHub Models (OpenAI-compatible, works through corporate proxies)
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_MODEL = os.getenv("GITHUB_MODEL", "gpt-4o-mini")

# Ollama (local, no API key, no network needed)
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# ── Embeddings ────────────────────────────────────────────────────────────────
# "local" → sentence-transformers (CPU, no API key needed)
# "openai" → text-embedding-3-small (requires OPENAI_API_KEY)
EMBEDDING_BACKEND = os.getenv("EMBEDDING_BACKEND", "local").lower()

# ── RAG / ChromaDB ────────────────────────────────────────────────────────────
CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "tspec_telecom")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "400"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))
TOP_K_RETRIEVAL = int(os.getenv("TOP_K_RETRIEVAL", "4"))
TOP_K_SUMMARIZE = int(os.getenv("TOP_K_SUMMARIZE", "6"))

# ── Dataset ───────────────────────────────────────────────────────────────────
TSPEC_DATASET = "rasoul-nikbakht/TSpec-LLM"
TSPEC_SAMPLE_SIZE = int(os.getenv("TSPEC_SAMPLE_SIZE", "200"))

# ── Validation ────────────────────────────────────────────────────────────────
# Answers with confidence below this value trigger the human-approval node
# Set conservatively low so genuine answers always reach the user
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.45"))

# ── SSL ──────────────────────────────────────────────────────────────────────
# Set SSL_VERIFY=false in .env when behind a corporate proxy that does
# TLS inspection (self-signed certificate in certificate chain).
_ssl_raw = os.getenv("SSL_VERIFY", "true").strip().lower()
SSL_VERIFY: bool = _ssl_raw not in ("false", "0", "no", "off")

# ── API server ────────────────────────────────────────────────────────────────
API_HOST = os.getenv("API_HOST", "127.0.0.1")
API_PORT = int(os.getenv("API_PORT", "8000"))
API_BASE_URL = f"http://{API_HOST}:{API_PORT}"
