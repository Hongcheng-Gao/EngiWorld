#!/usr/bin/env python3
"""Audit task instructions and add explicit output paths as artifact_paths.

The instruction remains the source of truth. Evaluator, init, and ground-truth
files are used only to disambiguate names already present in the instruction.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path, PurePosixPath, PureWindowsPath


OUTPUT_EXTENSIONS = {
    ".3mf", ".aedt", ".ai", ".blend", ".bmp", ".brd", ".cae", ".cas",
    ".csv", ".dat", ".db", ".doc", ".docx", ".dxf", ".edif", ".edn",
    ".f3d", ".fcstd", ".fem", ".foam", ".gbr", ".gcode", ".gif", ".glb",
    ".gltf", ".h5", ".iges", ".igs", ".ifc", ".inp", ".ipc2581", ".jpeg",
    ".jpg", ".json", ".kicad_pcb", ".kicad_pro", ".kicad_sch", ".m", ".msh",
    ".md", ".mtl", ".nc", ".obj", ".odb", ".olb", ".opj", ".osm", ".osw",
    ".out", ".outjob", ".pcbdoc", ".pdf", ".png", ".prjpcb", ".prt", ".ps",
    ".ps1", ".py", ".rb", ".rpt", ".rst", ".rth", ".sat", ".scad", ".sch", ".schdoc",
    ".sldasm", ".sldprt", ".step", ".stl", ".svg", ".tif", ".tiff", ".txt",
    ".vtu", ".wbpj", ".xlsx", ".xml", ".x_t", ".xdmf", ".yaml", ".yml", ".zip",
    ".dsn", ".drl", ".end", ".err", ".fst", ".log", ".sql",
}

NEVER_ARCHIVE_EXTENSIONS = {".exe", ".bat", ".cmd", ".dll", ".lnk", ".sh"}
HELPER_NAMES = {
    "eval.py", "artifact_contract.json", "problem_spec.json", "objective.json",
    "handoff_notes.md", "mechanical_requirements.json", "connector_keepouts.csv",
}
POSITIVE_RE = re.compile(
    r"(?i)save|saved|saving|output|deliver|produce|create|write|export|render|"
    r"submit|submission|result|artifact|generate|generated|keep it|直接|保存|输出|交付"
)
NEGATIVE_RE = re.compile(
    r"(?i)desktop contains|input(?:s)?|read|open|starter|available|launch|executable|"
    r"working on|source file|uploaded|provided|located|路径|打开|读取|输入"
)
EXT_PATTERN = (
    r"3mf|aedt|ai|blend|bmp|brd|cae|cas|csv|dat|db|docx?|dxf|edif|edn|f3d|"
    r"fcstd|fem|foam|gbr|gcode|gif|glb|gltf|h5|iges|igs|ifc|inp|ipc2581|jpe?g|json|"
    r"kicad_pcb|kicad_pro|kicad_sch|m|msh|mtl|nc|obj|odb|osm|pdf|png|prt|ps|rpt|"
    r"rst|rth|sat|scad|sch|schdoc|sldasm|sldprt|step|stl|svg|tiff?|txt|vtu|wbpj|"
    r"xlsx|xml|x_t|xdmf|yaml|yml|zip|md|olb|opj|osw|out|outjob|pcbdoc|prjpcb|ps1|py|rb|"
    r"dsn|drl|end|err|fst|log|sql"
)
FILE_TOKEN_RE = re.compile(
    rf"(?<![A-Za-z0-9_.-])((?:"
    rf"[A-Za-z]:\\Users\\(?:user|User)\\Desktop\\(?:[A-Za-z0-9_+()-]+\\)*|"
    rf"/home/user/Desktop/(?:[A-Za-z0-9_+()-]+/)*|"
    rf"(?:[A-Za-z0-9_+()-]+[\\/])?"
    rf")[A-Za-z0-9][A-Za-z0-9_.+()-]*\.(?:{EXT_PATTERN}))"
    rf"(?![A-Za-z0-9_-])",
    re.IGNORECASE,
)
ABS_POSIX_RE = re.compile(rf"/home/user/Desktop/(?:[A-Za-z0-9_.+()-]+/)*[A-Za-z0-9][A-Za-z0-9_.+()-]*\.(?:{EXT_PATTERN})", re.I)
ABS_WINDOWS_RE = re.compile(rf"[A-Za-z]:\\Users\\(?:user|User)\\Desktop\\(?:[A-Za-z0-9_.+()-]+\\)*[A-Za-z0-9][A-Za-z0-9_.+()-]*\.(?:{EXT_PATTERN})", re.I)
CODE_SPAN_RE = re.compile(r"`([^`]+)`")


def iter_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from iter_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from iter_strings(item)


def clean_path_token(value: str) -> str:
    return value.strip().rstrip(".,;:)]}\"'")


def basename(value: str) -> str:
    if "\\" in value or re.match(r"^[A-Za-z]:", value):
        return PureWindowsPath(value).name
    return PurePosixPath(value).name


def suffix(value: str) -> str:
    name = basename(value)
    return Path(name).suffix.lower()


def task_platform(task: dict) -> str:
    task_id = str(task.get("id", "")).lower()
    if task_id.endswith("-windows"):
        return "windows"
    if task_id.endswith("-ubuntu"):
        return "ubuntu"
    for text in iter_strings(task.get("config", [])):
        if re.match(r"^[A-Za-z]:\\", text):
            return "windows"
        if text.startswith("/home/"):
            return "ubuntu"
    return "unknown"


def desktop_path(name: str, platform: str) -> str:
    if platform == "windows":
        return str(PureWindowsPath(r"C:\Users\user\Desktop") / name)
    return str(PurePosixPath("/home/user/Desktop") / name)


def config_destinations(task: dict) -> set[str]:
    values = set()

    def visit(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key == "path" and isinstance(item, str):
                    values.add(clean_path_token(item))
                elif key != "local_path":
                    visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    visit(task.get("config", []))
    return values


def evaluator_vm_files(task: dict) -> set[str]:
    found = set()

    def visit(value):
        if isinstance(value, dict):
            if value.get("type") == "vm_file" and isinstance(value.get("path"), str):
                found.add(clean_path_token(value["path"]))
            for item in value.values():
                visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    visit(task.get("evaluator", {}))
    return found


def ground_truth_names(task_dir: Path) -> set[str]:
    gt = task_dir / "ground_truth"
    if not gt.exists():
        return set()
    return {path.name for path in gt.rglob("*") if path.is_file()}


def ground_truth_relpaths(task_dir: Path) -> set[str]:
    gt = task_dir / "ground_truth"
    if not gt.exists():
        return set()
    return {path.relative_to(gt).as_posix().lower() for path in gt.rglob("*") if path.is_file()}


def evaluator_desktop_paths(task_dir: Path) -> set[str]:
    eval_path = task_dir / "eval.py"
    if not eval_path.exists():
        return set()
    text = eval_path.read_text(encoding="utf-8", errors="replace")
    values = set()
    for match in ABS_POSIX_RE.finditer(text):
        values.add(clean_path_token(match.group(0)))
    for match in ABS_WINDOWS_RE.finditer(text):
        values.add(clean_path_token(match.group(0)))
    return values


def instruction_file_mentions(instruction: str) -> list[tuple[str, int, str]]:
    mentions = []
    seen = set()
    for match in FILE_TOKEN_RE.finditer(instruction):
        raw = clean_path_token(match.group(1))
        key = (raw.lower(), match.start())
        if key in seen:
            continue
        seen.add(key)
        start = max(0, match.start() - 180)
        end = min(len(instruction), match.end() + 180)
        mentions.append((raw, match.start(), instruction[start:end]))
    return mentions


def direct_absolute_mentions(instruction: str) -> set[str]:
    values = set()
    for pattern in (ABS_POSIX_RE, ABS_WINDOWS_RE):
        for match in pattern.finditer(instruction):
            value = clean_path_token(match.group(0))
            values.add(value)
    return values


def explicit_output_directories(instruction: str, inputs: set[str]) -> list[tuple[str, str]]:
    values = []
    normalized_inputs = {item.rstrip("/\\").lower() for item in inputs}
    for match in CODE_SPAN_RE.finditer(instruction):
        value = match.group(1).strip()
        if not (
            re.fullmatch(r"/home/user/Desktop/(?:[A-Za-z0-9_+().-]+/)+", value)
            or re.fullmatch(r"[A-Za-z]:\\Users\\(?:user|User)\\Desktop\\(?:[A-Za-z0-9_+(). -]+\\)+", value, re.I)
        ):
            continue
        before = instruction[max(0, match.start() - 100): match.start()]
        context = instruction[max(0, match.start() - 120): min(len(instruction), match.end() + 120)]
        normalized_value = value.rstrip("/\\").lower()
        if normalized_value in normalized_inputs or any(
            item.startswith(normalized_value + ("\\" if "\\" in normalized_value else "/"))
            for item in normalized_inputs
        ):
            continue
        if re.search(r"(?i)create|save|output|deliver|produce|write|generate|retain", before):
            values.append((value.rstrip("/\\"), context))
    return values


def is_output_context(context: str) -> bool:
    return bool(POSITIVE_RE.search(context)) and not (
        NEGATIVE_RE.search(context) and not re.search(r"(?i)save as|save to|output|deliver|produce|write|export|render", context)
    )


def explicitly_rewrites_input(instruction: str, occurrence: int, name: str) -> bool:
    start = max(0, occurrence - 90)
    end = min(len(instruction), occurrence + len(name) + 90)
    context = instruction[start:end]
    return bool(re.search(r"(?i)(?:save|export|write|overwrite|update|modify)[^.\n]{0,80}" + re.escape(basename(name)), context))


def analyze_task(json_path: Path, root: Path) -> dict:
    task = json.loads(json_path.read_text(encoding="utf-8"))
    instruction = str(task.get("instruction", ""))
    platform = task_platform(task)
    task_dir = json_path.parent
    inputs = config_destinations(task)
    input_names = {basename(item).lower() for item in inputs}
    vm_files = evaluator_vm_files(task)
    eval_paths = evaluator_desktop_paths(task_dir)
    gt_names = ground_truth_names(task_dir)
    gt_relpaths = ground_truth_relpaths(task_dir)
    expected_names = {basename(item).lower() for item in vm_files}
    expected_names.update(name.lower() for name in gt_names)
    expected_names.difference_update(HELPER_NAMES)

    paths = set()
    evidence = []
    rejected = []

    for value, _ in explicit_output_directories(instruction, inputs):
        paths.add(value)
        evidence.append(f"instruction explicitly creates output directory: {value}")

    for name, occurrence, context in instruction_file_mentions(instruction):
        ext = suffix(name)
        lower_name = basename(name).lower()
        if ext not in OUTPUT_EXTENSIONS or ext in NEVER_ARCHIVE_EXTENSIONS or lower_name in HELPER_NAMES:
            continue
        supported = lower_name in expected_names or is_output_context(context)
        input_only = lower_name in input_names and not (
            any(basename(item).lower() == lower_name for item in vm_files)
            and lower_name in {item.lower() for item in gt_names}
            and explicitly_rewrites_input(instruction, occurrence, name)
        )
        if not supported or input_only:
            continue
        if name.startswith("/home/") or re.match(r"^[A-Za-z]:\\", name):
            value = clean_path_token(name)
        else:
            relative_name = name.replace("\\", "/")
            if "/" in relative_name:
                evaluator_suffixes = {item.replace("\\", "/").lower() for item in vm_files | eval_paths}
                if relative_name.lower() not in gt_relpaths and not any(
                    item.endswith("/" + relative_name.lower()) for item in evaluator_suffixes
                ):
                    relative_name = basename(name)
            value = desktop_path(relative_name, platform)
        paths.add(value)
        evidence.append(f"instruction names output {basename(name)}; desktop path confirmed for {platform}")

    # A vm_file is strong evidence only when its filename is explicitly named in the instruction.
    instruction_lower = instruction.lower()
    mentioned_names = {
        basename(item[0]).lower() for item in instruction_file_mentions(instruction)
    }
    for value in vm_files:
        name = basename(value)
        if name.lower() in mentioned_names and suffix(value) not in NEVER_ARCHIVE_EXTENSIONS:
            paths.add(value)
            evidence.append(f"instruction name + evaluator vm_file: {value}")

    paths = sorted(paths, key=str.lower)
    directory_paths = [item.rstrip("/\\") for item in paths if not Path(basename(item)).suffix]
    if directory_paths:
        paths = [
            item for item in paths
            if item.rstrip("/\\") in directory_paths
            or not any(
                item.lower().startswith(directory.lower() + ("\\" if "\\" in directory else "/"))
                for directory in directory_paths
            )
        ]
    # When the same filename is mentioned both bare and under an explicit output
    # subdirectory, retain the more specific path.
    by_name = {}
    for item in paths:
        by_name.setdefault(basename(item).lower(), []).append(item)
    for items in by_name.values():
        if len(items) < 2:
            continue
        depths = {item: len(PureWindowsPath(item).parts) if "\\" in item else len(PurePosixPath(item).parts) for item in items}
        max_depth = max(depths.values())
        paths = [item for item in paths if item not in items or depths[item] == max_depth]
    explicit_expected = sorted(
        name for name in expected_names
        if name
        and name in mentioned_names
        and name not in input_names
        and Path(name).suffix.lower() in OUTPUT_EXTENSIONS
    )
    covered_names = {basename(item).lower() for item in paths}
    missing_named = [name for name in explicit_expected if name not in covered_names]

    vague_native_outputs = bool(re.search(
        r"(?i)(?:save|deliver|produce)[^.\n]{0,100}native (?:model|solver|result|project|design) artifact",
        instruction,
    ))
    if platform == "unknown":
        status = "人工复核"
        reason = "无法确定运行环境是 Windows 还是 Ubuntu，不能安全生成绝对路径。"
    elif vague_native_outputs:
        status = "人工复核"
        reason = "instruction 要求保存原生模型或求解结果，但没有给这些交付物明确文件名；已有明确路径也可能只覆盖部分输出。"
    elif not paths:
        status = "人工复核"
        reason = "instruction 未明确给出可安全归档的输出文件名，或只要求保存原生产物但没有命名。"
    elif missing_named:
        status = "人工复核"
        reason = "instruction 点名的部分预期输出未能确定路径：" + ", ".join(missing_named)
    else:
        status = "可自动添加"
        reason = "instruction 已明确输出文件名，可映射到任务桌面路径。"

    rel = json_path.relative_to(root).as_posix()
    family = rel.split("/")[1] if "/" in rel else ""
    return {
        "task_path": rel,
        "task_id": task.get("id", ""),
        "family": family,
        "snapshot": task.get("snapshot", ""),
        "platform": platform,
        "instruction": instruction,
        "status": status,
        "artifact_paths": paths,
        "reason": reason,
        "evidence": sorted(set(evidence)),
        "evaluator_vm_files": sorted(vm_files),
        "evaluator_desktop_paths": sorted(eval_paths),
        "ground_truth_files": sorted(gt_names),
        "config_input_paths": sorted(inputs),
        "rejected_mentions": sorted(set(rejected)),
    }


def insert_artifact_paths(json_path: Path, paths: list[str]) -> bool:
    text = json_path.read_text(encoding="utf-8")
    task = json.loads(text)
    if task.get("artifact_paths") == paths:
        return False
    if "artifact_paths" in task:
        raise ValueError(f"Refusing to replace existing artifact_paths in {json_path}")
    rendered = json.dumps(paths, ensure_ascii=False, indent=2)
    rendered = "\n".join("  " + line for line in rendered.splitlines())
    marker = '\n  "evaluator":'
    if marker not in text:
        raise ValueError(f"Cannot find top-level evaluator insertion point in {json_path}")
    replacement = f'\n  "artifact_paths": {rendered.lstrip()},\n  "evaluator":'
    updated = text.replace(marker, replacement, 1)
    json.loads(updated)
    json_path.write_text(updated, encoding="utf-8")
    return True


def write_reports(rows: list[dict], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "artifact_paths_audit.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    columns = [
        "task_path", "task_id", "family", "snapshot", "platform", "status",
        "artifact_paths", "reason", "evidence", "evaluator_vm_files",
        "evaluator_desktop_paths", "ground_truth_files", "config_input_paths",
        "instruction",
    ]
    with (output_dir / "artifact_paths_audit.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            flat = dict(row)
            for key in columns:
                if isinstance(flat.get(key), list):
                    flat[key] = "\n".join(flat[key])
            writer.writerow({key: flat.get(key, "") for key in columns})


def validate_applied(rows: list[dict], root: Path) -> dict:
    errors = []
    declared_paths = 0
    for row in rows:
        json_path = root / row["task_path"]
        task = json.loads(json_path.read_text(encoding="utf-8"))
        actual = task.get("artifact_paths")
        if row["status"] == "可自动添加":
            if actual != row["artifact_paths"]:
                errors.append(f"artifact_paths mismatch: {row['task_path']}")
                continue
            declared_paths += len(actual)
            if len(actual) != len(set(item.lower() for item in actual)):
                errors.append(f"duplicate artifact path: {row['task_path']}")
            input_paths = {item.rstrip("/\\").lower() for item in row["config_input_paths"]}
            for value in actual:
                lower = value.lower().rstrip("/\\")
                if not (
                    lower.startswith("/home/user/desktop/")
                    or lower.startswith("c:\\users\\user\\desktop\\")
                ):
                    errors.append(f"path outside task Desktop: {row['task_path']} -> {value}")
                if lower in {"/home/user/desktop", r"c:\users\user\desktop"}:
                    errors.append(f"whole Desktop must not be archived: {row['task_path']}")
                if lower in input_paths:
                    errors.append(f"input path archived: {row['task_path']} -> {value}")
                if basename(value).lower() in HELPER_NAMES:
                    errors.append(f"evaluator/helper path archived: {row['task_path']} -> {value}")
        elif actual is not None:
            errors.append(f"review task was modified: {row['task_path']}")
    if errors:
        raise ValueError("\n".join(errors[:50]))
    return {
        "json_files": len(rows),
        "with_artifact_paths": sum(row["status"] == "可自动添加" for row in rows),
        "without_artifact_paths": sum(row["status"] != "可自动添加" for row in rows),
        "declared_paths": declared_paths,
        "validation_errors": 0,
    }
    review = [row for row in rows if row["status"] != "可自动添加"]
    with (output_dir / "artifact_paths_human_review.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in review:
            flat = dict(row)
            for key in columns:
                if isinstance(flat.get(key), list):
                    flat[key] = "\n".join(flat[key])
            writer.writerow({key: flat.get(key, "") for key in columns})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    files = sorted((root / "task").glob("**/task-*.json"))
    rows = [analyze_task(path, root) for path in files]
    changed = 0
    if args.apply:
        for row in rows:
            if row["status"] == "可自动添加":
                changed += int(insert_artifact_paths(root / row["task_path"], row["artifact_paths"]))
    write_reports(rows, args.output_dir.resolve())
    validation = validate_applied(rows, root) if args.apply else None
    counts = Counter(row["status"] for row in rows)
    family_counts = Counter((row["family"], row["status"]) for row in rows)
    print(json.dumps({
        "tasks": len(rows),
        "changed": changed,
        "status": dict(counts),
        "by_family": {f"{key[0]} | {key[1]}": value for key, value in sorted(family_counts.items())},
        "validation": validation,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
