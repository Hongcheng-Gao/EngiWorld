#!/usr/bin/env python3
from __future__ import annotations

import ast
import csv
import math
import os
from pathlib import Path
import re
import subprocess
import sys


FLOAT_RE = re.compile(
    r"(?<![A-Za-z0-9_])[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?(?![A-Za-z0-9_])"
)


def desktop_root() -> Path:
    return Path(os.environ.get("ENGIWORLD_DESKTOP", "/home/user/Desktop"))


def require_nonempty(root: Path, names: list[str]) -> None:
    for name in names:
        path = root / name
        if not path.is_file() or path.stat().st_size == 0:
            raise ValueError(f"missing or empty file: {name}")


def remove_outputs(root: Path, names: list[str]) -> None:
    for name in names:
        path = root / name
        if path.exists():
            path.unlink()


def parse_floats(path: Path, expected_count: int | None = None) -> list[float]:
    values = [float(token) for token in FLOAT_RE.findall(path.read_text(encoding="utf-8"))]
    if expected_count is not None and len(values) != expected_count:
        raise ValueError(f"expected {expected_count} numeric fields in {path.name}, found {len(values)}")
    if not all(math.isfinite(value) for value in values):
        raise ValueError(f"non-finite numeric field in {path.name}")
    return values


def floats_close(
    actual: list[float],
    expected: list[float],
    *,
    rel_tol: float = 1e-4,
    abs_tol: float = 1e-3,
) -> bool:
    return len(actual) == len(expected) and all(
        math.isclose(a, e, rel_tol=rel_tol, abs_tol=abs_tol)
        for a, e in zip(actual, expected)
    )


def parse_script(path: Path) -> ast.AST:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def call_counts(tree: ast.AST) -> dict[str, int]:
    counts: dict[str, int] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name):
            name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            name = node.func.attr
        else:
            continue
        counts[name] = counts.get(name, 0) + 1
    return counts


def require_calls(tree: ast.AST, requirements: dict[str, int]) -> None:
    counts = call_counts(tree)
    for name, minimum in requirements.items():
        if counts.get(name, 0) < minimum:
            raise ValueError(f"required call {name!r} not found {minimum} time(s)")


def require_source_tokens(path: Path, tokens: list[str]) -> None:
    source = path.read_text(encoding="utf-8")
    for token in tokens:
        if token not in source:
            raise ValueError(f"required source token missing: {token}")


def run_submission(
    root: Path,
    script_name: str,
    outputs: list[str],
    *,
    timeout: int = 180,
) -> ast.AST:
    script = root / script_name
    require_nonempty(root, [script_name])
    tree = parse_script(script)
    remove_outputs(root, outputs)
    completed = subprocess.run(
        [sys.executable, str(script)],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"{script_name} exited {completed.returncode}: {completed.stderr[-2000:]}"
        )
    require_nonempty(root, outputs)
    return tree


def read_numeric_csv(path: Path, rows: int, columns: int, *, header: list[str] | None = None):
    with path.open("r", encoding="utf-8", newline="") as handle:
        records = list(csv.reader(handle))
    if header is not None:
        if not records or [cell.strip() for cell in records[0]] != header:
            raise ValueError(f"unexpected CSV header in {path.name}")
        records = records[1:]
    if len(records) != rows:
        raise ValueError(f"expected {rows} CSV rows in {path.name}, found {len(records)}")
    matrix = []
    for record in records:
        if len(record) != columns:
            raise ValueError(f"expected {columns} CSV columns in {path.name}")
        values = [float(cell.strip()) for cell in record]
        if not all(math.isfinite(value) for value in values):
            raise ValueError(f"non-finite CSV value in {path.name}")
        matrix.append(values)
    return matrix


def print_result(ok: bool) -> int:
    print("True" if ok else "False")
    return 0
