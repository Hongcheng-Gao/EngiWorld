"""Outcome categories must preserve the distinction between cause and symptoms."""
from __future__ import annotations

MODEL_ENVIRONMENT_ERROR_CATEGORY = "model_environment"  # legacy records only


def classify_task_error(error: str | None, error_category: str | None) -> str | None:
    # A disconnect or screenshot HTTP 500 alone is not causal evidence.
    if error and error_category == MODEL_ENVIRONMENT_ERROR_CATEGORY:
        return "infra"
    return error_category
