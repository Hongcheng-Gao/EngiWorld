"""Environment failures must not become valid model scores."""


class EvaluationExecutionError(RuntimeError):
    """The evaluator did not produce a valid result."""

    error_category = "infra"


class EvaluationDependencyError(EvaluationExecutionError):
    """A dependency needed by the evaluator is unavailable."""


class DesktopPreparationError(RuntimeError):
    """The guest desktop could not be set to the requested evaluation geometry."""

    error_category = "infra"
