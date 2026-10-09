"""Paper-aligned task names and compatibility with historical experiment paths."""

TASK_TYPES = (
    "single-software-execution", "software-selection", "vision-guided-modeling",
    "design-optimization", "cross-software-coordination", "open-environment-engineering",
)
LEGACY_PREFIXES = {
    "single-software/": "single-software-execution/",
    "multi-software/": "cross-software-coordination/",
    "quantitative-design/": "design-optimization/",
    "image-based-modeling/": "vision-guided-modeling/",
    "open-ended/": "open-environment-engineering/",
    "task-c/": "single-software-execution/cli/",
    "task-v/": "single-software-execution/gui/",
    "multi/": "cross-software-coordination/",
    "open/": "software-selection/",
    "quantified/": "design-optimization/",
    "init-image/messgae/": "vision-guided-modeling/",
    "init-image/message/": "vision-guided-modeling/",
    "top-10-hardest/": "open-environment-engineering/",
}
LEGACY_KINDS = {
    "single-software": "single-software-execution", "multi-software": "cross-software-coordination",
    "quantitative-design": "design-optimization", "image-based-modeling": "vision-guided-modeling",
    "open-ended": "open-environment-engineering",
    "task-c": "single-software-execution", "task-v": "single-software-execution", "reverse": "single-software-execution",
    "multi": "cross-software-coordination", "open": "software-selection",
    "quantified": "design-optimization", "init-image": "vision-guided-modeling",
    "top-10-hardest": "open-environment-engineering",
}


def canonical_prefix(path: str) -> str:
    normalized = str(path).replace("\\", "/").lstrip("/")
    for before, after in LEGACY_PREFIXES.items():
        if normalized == before.rstrip("/"):
            return after.rstrip("/")
        if normalized.startswith(before):
            return after + normalized[len(before):]
    return normalized


def task_kind(value: str) -> str:
    return LEGACY_KINDS.get(value, value)
