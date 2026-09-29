"""Load benchmark tasks from the local task directory."""

from __future__ import annotations

import json
import hashlib
import importlib.util
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Iterable

from engiworld.scheduler.schemas import TaskSpec
from engiworld.task_names import TASK_TYPES, canonical_prefix, task_kind


DEFAULT_OPEN_ENDED_SNAPSHOT = "top-10"


def _task_sort_key(path: Path) -> tuple[str, ...]:
    return path.parts


def _domain_from_path(task_root: Path, task_file: Path) -> str:
    relative = task_file.relative_to(task_root)
    # Keep all grouping levels before the task directory (including interface).
    return "/".join(relative.parts[:-2])


def _task_kind_from_path(task_root: Path, task_file: Path) -> str:
    relative = task_file.relative_to(task_root)
    return task_kind(relative.parts[0]) if relative.parts else "unknown"


def _app_from_path(task_root: Path, task_file: Path) -> str:
    parts = canonical_prefix(task_file.relative_to(task_root).as_posix()).split("/")
    if len(parts) >= 4 and parts[0] in TASK_TYPES and parts[1] in {"gui", "cli"}:
        return parts[2]
    if parts[0] == "open-ended":
        return "open-ended"
    if len(parts) >= 3:
        return parts[1]
    return "unknown"


def _infer_os_type(task_json: dict) -> str:
    task_id = str(task_json.get("id", "")).lower()
    if task_id.endswith("-windows") or "-windows" in task_id:
        return "Windows"
    return "Ubuntu"


def infer_engiworld_eval_mode(task_path: str | Path) -> str:
    """Map an EngiWorld task path to its required interaction mode."""
    parts = canonical_prefix(str(task_path)).strip("/").lower().split("/")
    if not parts:
        raise ValueError(f"Cannot infer eval mode from empty task path: {task_path!r}")
    if parts[0] in TASK_TYPES and len(parts) >= 2 and parts[1] in {"cli", "gui"}:
        return parts[1]
    if parts[0] == "single-software" and len(parts) >= 2:
        if parts[1] in {"cli", "gui"}:
            return parts[1]
        raise ValueError(f"Cannot infer EngiWorld interface from task path: {task_path!r}")
    if parts[0] == "open-ended":
        return "cli"
    if parts[0] in {"software-selection", "multi-software", "quantitative-design", "image-based-modeling", "reverse"} and len(parts) >= 2:
        if parts[1].startswith("cli-"):
            return "cli"
        if parts[1].startswith("gui-"):
            return "gui"
        raise ValueError(f"Cannot infer EngiWorld eval mode from task path: {task_path!r}")
    if parts[0] == "init-image" and len(parts) >= 3:
        if parts[2].startswith("cli-"):
            return "cli"
        if parts[2].startswith("gui-"):
            return "gui"
        raise ValueError(f"Cannot infer EngiWorld init-image mode from task path: {task_path!r}")
    # Preserve arena-osworld's ability to run ordinary OSWorld GUI task sets.
    return "gui"


def discover_task_files(
    task_root: str | Path,
    path_prefixes: Iterable[str] | None = None,
    limit: int | None = None,
) -> list[Path]:
    root = Path(task_root).expanduser().resolve()
    if not root.exists():
        raise FileNotFoundError(f"Task root does not exist: {root}")

    prefixes = [prefix.strip("/") for prefix in path_prefixes or [] if prefix.strip("/")]
    aliases_path = root / "aliases.json"
    if aliases_path.is_file():
        aliases = json.loads(aliases_path.read_text(encoding="utf-8"))
        expanded = list(prefixes)
        for prefix in prefixes:
            for old, new in aliases.items():
                if old == prefix or old.startswith(prefix + "/"):
                    expanded.append(new + "/")
                elif prefix.startswith(old + "/"):
                    expanded.append(new + prefix[len(old):])
        prefixes = expanded
    if prefixes:
        # Resolve exact directories before walking: selecting one task should not
        # traverse all input and ground-truth files in the full corpus.
        candidates: set[Path] = set()
        directories: list[Path] = []
        for prefix in set(prefixes):
            path = (root / prefix.rstrip("/")).resolve()
            if not path.is_relative_to(root):
                continue
            if path.is_file() and path.match("task-*.json"):
                candidates.add(path)
            elif path.is_dir():
                directories.append(path)
        visited: list[Path] = []
        for directory in sorted(directories, key=lambda path: len(path.parts)):
            if any(directory.is_relative_to(parent) for parent in visited):
                continue
            candidates.update(directory.glob("**/task-*.json"))
            visited.append(directory)
        files = sorted(candidates, key=_task_sort_key)
    else:
        files = sorted(root.glob("**/task-*.json"), key=_task_sort_key)
    if limit is not None:
        files = files[:limit]
    return files


def load_tasks(
    task_root: str | Path = "task",
    path_prefixes: Iterable[str] | None = None,
    limit: int | None = None,
    max_attempts: int = 3,
    task_id_suffix: str | None = None,
    benchmark: str = "engiworld",
    osworld_v2_path: str | Path | None = None,
    v2_image_ids: dict[str, str] | None = None,
) -> list[TaskSpec]:
    if benchmark == "osworld-v2":
        return load_v2_tasks(
            task_root=task_root,
            path_prefixes=path_prefixes,
            limit=limit,
            max_attempts=max_attempts,
            task_id_suffix=task_id_suffix,
            osworld_v2_path=osworld_v2_path,
            image_ids=v2_image_ids,
        )
    if benchmark not in {"engiworld", "osworld-v1"}:
        raise ValueError(f"Unsupported benchmark: {benchmark!r}")
    root = Path(task_root).expanduser().resolve()
    tasks: list[TaskSpec] = []
    for task_file in discover_task_files(root, path_prefixes=path_prefixes, limit=limit):
        with task_file.open("r", encoding="utf-8") as file:
            task_json = json.load(file)

        task_dir = task_file.parent
        example_id = task_dir.name
        domain = _domain_from_path(root, task_file)
        base_task_id = task_dir.relative_to(root).as_posix()
        eval_mode = infer_engiworld_eval_mode(base_task_id)
        task_id = f"{base_task_id}@{task_id_suffix}" if task_id_suffix else base_task_id
        snapshot = _resolve_snapshot(base_task_id, str(task_json["snapshot"]))
        tasks.append(
            TaskSpec(
                task_id=task_id,
                domain=domain,
                example_id=example_id,
                max_attempts=max_attempts,
                metadata={
                    "base_task_id": base_task_id,
                    "task_id_suffix": task_id_suffix or "",
                    "source_task_id": str(task_json["id"]),
                    "snapshot": snapshot,
                    "os_type": _infer_os_type(task_json),
                    "app": _app_from_path(root, task_file),
                    "task_kind": _task_kind_from_path(root, task_file),
                    "eval_mode": eval_mode,
                    "task_path": task_file.relative_to(root).as_posix(),
                    "task_dir": task_dir.relative_to(root).as_posix(),
                    "task_json": task_json,
                },
            )
        )
    return tasks


def _resolve_snapshot(base_task_id: str, configured_snapshot: str) -> str:
    """Keep Open-ended tasks on the dedicated blank image by default."""
    if (
        canonical_prefix(base_task_id).startswith("open-ended/")
        and configured_snapshot.strip().lower() == "top-10"
    ):
        return (
            os.getenv("ENGIWORLD_OPEN_ENDED_SNAPSHOT", os.getenv("ARENA_TOP10_SNAPSHOT", DEFAULT_OPEN_ENDED_SNAPSHOT)).strip()
            or DEFAULT_OPEN_ENDED_SNAPSHOT
        )
    return configured_snapshot


def load_v2_tasks(
    task_root: str | Path,
    path_prefixes: Iterable[str] | None,
    limit: int | None,
    max_attempts: int,
    task_id_suffix: str | None,
    osworld_v2_path: str | Path | None,
    image_ids: dict[str, str] | None,
) -> list[TaskSpec]:
    """Load OSWorld V2's gated Python task classes without importing V1 code."""
    root = Path(task_root).expanduser().resolve()
    v2_root = Path(osworld_v2_path or "third_party/OSWorld-V2").expanduser().resolve()
    if not root.exists():
        raise FileNotFoundError(f"Task root does not exist: {root}")
    if not v2_root.exists():
        raise FileNotFoundError(f"OSWorld V2 checkout not found: {v2_root}")

    candidates = sorted(root.glob("**/task_*.py"), key=_task_sort_key)
    prefixes = [prefix.strip("/") for prefix in path_prefixes or [] if prefix.strip("/")]
    if prefixes:
        candidates = [
            path
            for path in candidates
            if any(path.relative_to(root).as_posix().startswith(prefix) for prefix in prefixes)
        ]
    if limit is not None:
        candidates = candidates[:limit]

    task_path = str(v2_root)
    if task_path not in sys.path:
        sys.path.insert(0, task_path)
    from desktop_env.task_base import BaseTask

    tasks: list[TaskSpec] = []
    for task_file in candidates:
        example = _load_v2_task_class(task_file, BaseTask)
        source_task_id = str(_task_value(example, "id") or task_file.stem)
        platform = str(_task_value(example, "platform") or "linux")
        os_type = "Windows" if platform.lower().startswith("win") else "Ubuntu"
        image_id = (image_ids or {}).get(os_type) or (image_ids or {}).get(platform.lower())
        image_ref = str(image_id or _task_value(example, "image") or f"osworld-v2-{os_type.lower()}")
        relative = task_file.relative_to(root).as_posix()
        base_task_id = relative.removesuffix(".py")
        task_id = f"{base_task_id}@{task_id_suffix}" if task_id_suffix else base_task_id
        tasks.append(
            TaskSpec(
                task_id=task_id,
                domain=_v2_domain(root, task_file),
                example_id=source_task_id,
                max_attempts=max_attempts,
                metadata={
                    "benchmark": "osworld-v2",
                    "base_task_id": base_task_id,
                    "task_id_suffix": task_id_suffix or "",
                    "source_task_id": source_task_id,
                    "snapshot": image_ref,
                    "image_id": image_id or "",
                    "image_ref": image_ref,
                    "os_type": os_type,
                    "platform": platform,
                    "volume_size": _task_value(example, "volume_size"),
                    "instance_type": _task_value(example, "instance_type"),
                    "disable_vnc": bool(_task_value(example, "disable_vnc", False)),
                    "disable_recording": bool(_task_value(example, "disable_recording", False)),
                    "task_path": relative,
                },
            )
        )
    return tasks


def _load_v2_task_class(task_file: Path, base_task: type) -> object:
    module_name = "engiworld_v2_task_" + hashlib.sha256(
        str(task_file).encode("utf-8")
    ).hexdigest()[:16]
    spec = importlib.util.spec_from_file_location(module_name, task_file)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load OSWorld V2 task module: {task_file}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    if callable(getattr(module, "get_task", None)):
        return module.get_task()
    if isinstance(getattr(module, "TASK_CLASS", None), type):
        return module.TASK_CLASS()
    if callable(getattr(module, "Task", None)):
        return module.Task()
    for value in module.__dict__.values():
        if isinstance(value, type) and issubclass(value, base_task) and value is not base_task:
            return value()
    raise ValueError(f"No BaseTask implementation found in {task_file}")


def _task_value(task: object, name: str, default: object | None = None) -> object | None:
    getter = getattr(task, "get", None)
    if callable(getter):
        return getter(name, default)
    return getattr(task, name, default)


def _v2_domain(root: Path, task_file: Path) -> str:
    parts = task_file.relative_to(root).parts
    if "task_class" in parts:
        index = parts.index("task_class")
        return "/".join(parts[index + 1 : -1]) or "default"
    return "/".join(parts[:-1]) or "default"


def snapshot_counts(tasks: Iterable[TaskSpec]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for task in tasks:
        counts[str(task.metadata["snapshot"])] += 1
    return counts


def allocate_instances_by_snapshot(
    tasks: list[TaskSpec],
    total_instances: int,
) -> dict[str, int]:
    counts = snapshot_counts(tasks)
    if total_instances <= 0 or not counts:
        return {}
    if total_instances < len(counts):
        raise ValueError(
            f"Cannot cover {len(counts)} snapshots with only {total_instances} instances."
        )

    total_tasks = sum(counts.values())
    target_instances = min(total_instances, total_tasks)
    allocation = {snapshot: 1 for snapshot in counts}
    remaining = target_instances - len(allocation)

    if remaining <= 0:
        return allocation

    # The first instance already covers one task for every snapshot. Distribute
    # the remaining capacity according to the tasks that are still uncovered;
    # using the original task counts here would double-count that baseline and
    # can over-allocate small snapshots while starving larger ones.
    remaining_demand = {
        snapshot: count - 1
        for snapshot, count in counts.items()
    }
    total_remaining_demand = sum(remaining_demand.values())
    if remaining >= total_remaining_demand:
        return dict(counts)

    raw_extra = {
        snapshot: (demand / total_remaining_demand) * remaining
        for snapshot, demand in remaining_demand.items()
    }
    for snapshot, extra in raw_extra.items():
        whole = min(int(extra), remaining_demand[snapshot])
        allocation[snapshot] += whole
        remaining -= whole

    fractional = sorted(
        raw_extra,
        key=lambda snapshot: (
            raw_extra[snapshot] % 1,
            remaining_demand[snapshot],
            snapshot,
        ),
        reverse=True,
    )
    for snapshot in fractional:
        if remaining <= 0:
            break
        if allocation[snapshot] >= counts[snapshot]:
            continue
        allocation[snapshot] += 1
        remaining -= 1

    return allocation
