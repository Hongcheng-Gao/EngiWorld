"""Paper-aligned task names and compatibility with historical experiment paths."""

TASK_TYPES = (
    "single-software", "multi-software", "software-selection",
    "quantitative-design", "image-based-modeling", "open-ended",
)
LEGACY_PREFIXES = {
    "task-c/": "single-software/cli/",
    "task-v/": "single-software/gui/",
    "multi/": "multi-software/",
    "open/": "software-selection/",
    "quantified/": "quantitative-design/",
    "init-image/messgae/": "image-based-modeling/",
    "init-image/message/": "image-based-modeling/",
    "top-10-hardest/": "open-ended/",
}
LEGACY_KINDS = {
    "task-c": "single-software", "task-v": "single-software", "reverse": "single-software",
    "multi": "multi-software", "open": "software-selection",
    "quantified": "quantitative-design", "init-image": "image-based-modeling",
    "top-10-hardest": "open-ended",
}


def canonical_prefix(path: str) -> str:
    normalized = str(path).replace("\\", "/").lstrip("/")
    for before, after in LEGACY_PREFIXES.items():
        if normalized.startswith(before):
            return after + normalized[len(before):]
    return normalized


def task_kind(value: str) -> str:
    return LEGACY_KINDS.get(value, value)
