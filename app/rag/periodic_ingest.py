"""
periodic_ingest.py — optional background ingestion scheduler for ChromaDB.

This runs the existing ingestion pipeline on a configurable interval so the
vector store can be refreshed automatically on EC2 without manual intervention.
"""

import os
import threading
import time
from typing import Optional

from app.rag.ingest_tspec import run_ingestion
from app.services.config import (
    RAG_REFRESH_ENABLED,
    RAG_REFRESH_INTERVAL_MINUTES,
    RAG_REFRESH_ON_STARTUP,
)
from app.utils.logger import setup_logger

log = setup_logger("periodic_ingest")


def parse_bool(value: Optional[object]) -> bool:
    """Parse common truthy/falsey strings from environment variables."""
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def get_interval_seconds(interval_minutes: Optional[object] = None, raw_value: Optional[object] = None) -> int:
    """Convert configured minutes to seconds, with a safe default."""
    source = interval_minutes if interval_minutes is not None else raw_value
    if source is None:
        source = RAG_REFRESH_INTERVAL_MINUTES
    try:
        minutes = int(str(source).strip())
    except (TypeError, ValueError):
        return 60 * 60
    if minutes <= 0:
        return 60
    return minutes * 60


class PeriodicIngestionManager:
    """Run ingestion in a background thread on a configurable cadence."""

    def __init__(self) -> None:
        self.enabled = RAG_REFRESH_ENABLED
        self.interval_seconds = get_interval_seconds(raw_value=os.getenv("RAG_REFRESH_INTERVAL_MINUTES"))
        self.run_on_startup = RAG_REFRESH_ON_STARTUP
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        if not self.enabled:
            log.info("Periodic ingestion disabled; set RAG_REFRESH_ENABLED=true to enable it")
            return

        if self._thread and self._thread.is_alive():
            return

        self._stop_event.clear()
        if self.run_on_startup:
            self._run_once("startup")

        self._thread = threading.Thread(target=self._loop, name="periodic-ingest", daemon=True)
        self._thread.start()
        log.info("Periodic ingestion enabled every %s seconds", self.interval_seconds)

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)

    def _run_once(self, reason: str) -> None:
        try:
            log.info("Starting ingestion refresh (%s)", reason)
            run_ingestion(force_mock=False, reset=False)
            log.info("Ingestion refresh completed (%s)", reason)
        except Exception as exc:  # pragma: no cover - defensive logging
            log.exception("Periodic ingestion failed (%s): %s", reason, exc)

    def _loop(self) -> None:
        while not self._stop_event.wait(self.interval_seconds):
            self._run_once("interval")


periodic_ingest_manager = PeriodicIngestionManager()
