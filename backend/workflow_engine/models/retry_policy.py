"""Immutable retry metadata and deterministic backoff calculation."""

from __future__ import annotations

from dataclasses import dataclass

from ..exceptions import InvalidRetryPolicyError


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """Retry limits and metadata; it never performs actual waiting."""

    max_attempts: int = 1
    backoff: str = "exponential"
    initial_seconds: float = 1.0
    max_seconds: float = 30.0

    def __post_init__(self) -> None:
        if self.max_attempts <= 0:
            raise InvalidRetryPolicyError("RetryPolicy.max_attempts must be positive")
        if self.backoff not in {"fixed", "linear", "exponential"}:
            raise InvalidRetryPolicyError(
                "RetryPolicy.backoff must be fixed, linear, or exponential"
            )
        if self.initial_seconds < 0:
            raise InvalidRetryPolicyError(
                "RetryPolicy.initial_seconds cannot be negative"
            )
        if self.max_seconds < self.initial_seconds:
            raise InvalidRetryPolicyError(
                "RetryPolicy.max_seconds cannot be smaller than initial_seconds"
            )

    def permits_retry(self, current_attempt: int) -> bool:
        if current_attempt <= 0:
            raise InvalidRetryPolicyError("Current attempt must be positive")
        return current_attempt < self.max_attempts

    def delay_for_next_attempt(self, next_attempt: int) -> float:
        """Return deterministic delay metadata for attempt 2 or later."""

        if next_attempt < 2:
            raise InvalidRetryPolicyError("Retry attempt must be at least 2")
        retry_index = next_attempt - 1
        if self.backoff == "fixed":
            delay = self.initial_seconds
        elif self.backoff == "linear":
            delay = self.initial_seconds * retry_index
        else:
            delay = self.initial_seconds * (2 ** (retry_index - 1))
        return min(float(delay), float(self.max_seconds))
