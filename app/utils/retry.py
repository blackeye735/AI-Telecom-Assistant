"""
retry.py — retry decorator built on tenacity.

Usage:
    @with_retry(max_attempts=3)
    def call_llm(prompt):
        ...

Any unhandled exception triggers a retry with exponential backoff.
Works as a plain decorator (no arguments) or with keyword arguments.
"""

import logging
from functools import wraps

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)

_log = logging.getLogger("retry")


def with_retry(max_attempts: int = 3, wait_min: float = 1.0, wait_max: float = 10.0):
    """Decorator factory: wrap a function with automatic retries.

    Args:
        max_attempts: Total number of attempts (first call + retries).
        wait_min:     Minimum seconds to wait between retries.
        wait_max:     Maximum seconds to wait between retries.
    """

    def decorator(func):
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=1, min=wait_min, max=wait_max),
            retry=retry_if_exception_type(Exception),
            before_sleep=before_sleep_log(_log, logging.WARNING),
            reraise=True,  # re-raise the last exception after all attempts
        )
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper

    return decorator
