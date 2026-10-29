"""Outcome categories must preserve the distinction between cause and symptoms."""
from __future__ import annotations

MODEL_ENVIRONMENT_ERROR_CATEGORY = "model_environment"  # legacy records only


def classify_task_error(error: str | None, error_category: str | None) -> str | None:
    # A disconnect or screenshot HTTP 500 alone is not causal evidence.
    if error and error_category == MODEL_ENVIRONMENT_ERROR_CATEGORY:
        return "infra"
    return error_category


def outcome_fields(error, category, score):
    """Single-run summaries use the same incomplete states as Redis completion."""
    category = classify_task_error(error, category)
    if error:
        status = "api_incomplete" if category == "model_api" else "infra_incomplete"
        if category == "model_action_alt_f4":
            return {"status": "completed", "score": 0.0}
        return {"status": status, "evaluation_status": status, "score": None,
                "error_category": category or "infra"}
    return {"status": "completed", "evaluation_status": "completed", "score": score}
