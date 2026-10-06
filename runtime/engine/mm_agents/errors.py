"""Exceptions shared by OSWorld model-backed agents."""

from __future__ import annotations


class ModelAPIError(RuntimeError):
    """Raised after a model API call exhausts its retry budget."""

    error_category = "model_api"

    def __init__(self, message: str, *, provider: str, attempts: int) -> None:
        super().__init__(message)
        self.provider = provider
        self.attempts = attempts

