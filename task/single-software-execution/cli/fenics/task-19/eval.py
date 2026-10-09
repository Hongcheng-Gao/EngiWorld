#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path


FLOAT_RE = re.compile(r"(?<![A-Za-z0-9_])[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?(?![A-Za-z0-9_])")
PRIVATE_RUNNER_B64 = "eNp9V8tu2zoQ3fsrCK2oVhWaTXFhwIugzaK4aW+RBt0IBqFIVMJGJgWSTm0E/vc7M6QelpwaSGCS8zgzc2ZIr9SuM9az0vmM1cpl7LczOmNOVlZ6WLoj/PPHTrpVY82OdaV/atUDi3o/YLlafbu++/fmjm1YIsTNr+tb8ePu66/r+xvx+fr29qcQyWpVy4bVxntZC13uJNemlul6xeCjGqac0s6XugoHGeLJv4NcFMEP4NlbzfA8V/VfNa+9t+ph76fqnZWNOgDGOYr8pWz3Mp37aZLXoHLKX0msBKOnBH1GU7J1kg1Hq4luEgOu4FCYh9+y8o5XY8RHJduaTmnZGMsIBFOadvPKiMpAXG7Efx4riYfCBMOTSEcPVLEzEDFWQrcrleZRD8vqIDkFFpSX9jHNrXSmfZE8JXywheiADjl8fSmu1tstaXrzLDVoRsbktBZP8sCvPoWkVmbXqVbWIPR6Cjtl21IB3Lj3JNtOWoH5nOyia8SGvgnjGKa3UoIg1rsrrZMczwF1WQsvD55LDZEr/bhJ9r758E+SZqwBGOh247wl8XQs+wwOwWxL59hXyLnd76T2nFgJAO9tqR1A20k7yzvm9QXq5MVniJE72TYZm3B9+sHD/FFqaVUlSCl0xUIQd4XC/CEpMUoEe1oHXrZKS236VWVaYZrGSQ87EC2nuNJTsrAaEk5GhXwRr1S4kyClaTEu6ZLRIuLaXmqqZq+rNG/NH2l5mruuheiSPEmLD1fbN6AEd0VYoFE+xJr1OVgmpykrb+wxMoGy3g+PGEaYCbemrHkKJCi2+Lc0FHsXZSvTHUVrqtIro/lgN7oCdUQTzMTqzlk5IU2ah9riySiHRmGIiJ1y0NWPgzc3k+ubpxhygZmJuyQLM7pnc8YSeZBVMlEfOu3cAG2tSAwkoErUnbi7Bl762PS4xs6b1mfsSxwsYWIFiGGQOj6hOok9KRhFcbJdmobDhKOcVZQFQNMq5zlcSdAiXkzPOFlMzyuInpSu5SGb2kG3UkMdbOklnxq50I84YUeJ3HQYfg4D13r3R8FYTG7/u/4ikpSVuj4TxYlYtugsJnNpfMgG6Koa0KD0FFBB6Nl7drXuv33aXrYTwSZ4uyaU2d5oBE0AtfGLg7NoftzdkIX0bS8TfhTLgLd5Wdc8lCOb+qL5k6Z/NfsAk/o5MBA5C5c1UXBg6Rq6azn+A/seIEPQNLN7ou923o/5cWrMSZwrL3dnTA0X4rMUscmHEYjXRW/Zmb2tZNgbnVCPqXrTO1veCL3NC5lGZZrCeLMKoHpjcXJdLZMHCac7oNRHHrTyRoQedKEXserDCdxdXrHNhoVqDB2b9RsjW4tJrBcGI0ZgZWVsHZ8Pl/kCjCSIb7Opr3MxySNwqOukrnnM4mXSxNlM7t8a3AHi6sJJTP9w1NNnctWclT4NtMS4aU52ZRVeFxnbmXrfBuTLp+krPH/xBB6866lkhu9i5AsdTKb1u3c9lFPsBO3pKiOuFx+3A7driUmCJ81xaAV8go0QgjtQpbd6/o2W9/g8HFWh++UunankQtSq8kLk+w67l48hj5oZm1sZzSBxgylXzKQos3S0mnKAD5faRJ7IkM1BBTeQlPUbFihjvfIInbYp7/jKhbxHwPJQyc6zn0eEd3NQ+MsHN8/e2bDOqaFwhEK6+XejoYgfZ8S3pXIyPvvdvvU4jcabL44HGGOTO7jf3Y5vJ7pn4wNP6f6r257doYuJ5uhmi/3UTzNSCfOwswqeHvF32Xv6UZfX+13neMCKs8x68SyPbnNvoaeB8+H3wOp/QMBSug=="


def is_result_artifact(path: Path) -> bool:
    name = path.name.lower()
    return (
        any(k in name for k in ("summary", "result", "report", "diagnosis"))
        or path.suffix.lower() in {".txt", ".csv", ".xy", ".result"}
    )


def is_nonempty_file(path: Path) -> bool:
    if not is_result_artifact(path):
        return True
    return path.exists() and path.is_file() and path.stat().st_size > 0


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def parse_floats(text: str) -> list[float]:
    out: list[float] = []
    for token in FLOAT_RE.findall(text):
        try:
            out.append(float(token))
        except (TypeError, ValueError):
            continue
    return out


def write_result(path: Path, value: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"result": int(1 if value else 0)}, ensure_ascii=False) + "\n", encoding="utf-8")


def dotted_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = dotted_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


def assignment_expressions(tree: ast.AST) -> dict[str, list[ast.AST]]:
    assignments: dict[str, list[ast.AST]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    assignments.setdefault(target.id, []).append(node.value)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.value is not None:
            assignments.setdefault(node.target.id, []).append(node.value)
    return assignments


def expression_dependencies(
    node: ast.AST,
    assignments: dict[str, list[ast.AST]],
    seen: set[str] | None = None,
) -> set[str]:
    seen = set() if seen is None else seen
    dependencies: set[str] = set()
    if isinstance(node, ast.Name):
        if node.id in seen:
            return dependencies
        for value in assignments.get(node.id, []):
            dependencies.update(expression_dependencies(value, assignments, seen | {node.id}))
        return dependencies
    if isinstance(node, ast.Call):
        dependencies.add(dotted_name(node.func).lower().split(".")[-1])
        dependencies.update(expression_dependencies(node.func, assignments, seen))
        for argument in node.args:
            dependencies.update(expression_dependencies(argument, assignments, seen))
        for keyword in node.keywords:
            dependencies.update(expression_dependencies(keyword.value, assignments, seen))
        return dependencies
    for child in ast.iter_child_nodes(node):
        dependencies.update(expression_dependencies(child, assignments, seen))
    return dependencies


def summary_depends_on_surface_force(tree: ast.AST) -> bool:
    assignments = assignment_expressions(tree)
    required = {"assemble", "facetnormal"}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or dotted_name(node.func).lower().split(".")[-1] not in {"write", "write_text"}:
            continue
        if node.args and required.issubset(expression_dependencies(node.args[0], assignments)):
            return True
    return False


def execute_script(root: Path, filename: str, timeout: int = 240) -> set[str]:
    script = (root / filename).resolve()
    with tempfile.TemporaryDirectory(prefix="fenics-task19-eval-") as temp_dir:
        runner = Path(temp_dir) / "runner.py"
        runner.write_bytes(__import__("zlib").decompress(__import__("base64").b64decode(PRIVATE_RUNNER_B64)))
        completed = subprocess.run(
            [sys.executable, str(runner), str(script)], cwd=root,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=timeout,
        )
        if completed.returncode != 0:
            raise ValueError("lift_drag.py did not complete successfully")
        marker = "__EVAL_PRIVATE_CALLS__"
        if marker not in completed.stdout:
            raise ValueError("lift_drag.py produced no private execution evidence")
        evidence = json.loads(completed.stdout.rsplit(marker, 1)[1].splitlines()[0])
    return set(evidence.get(filename, []))


def check_lift_drag_script(path: Path) -> bool:
    try:
        source = read_text(path)
        tree = ast.parse(source, filename=path.name)
    except (OSError, SyntaxError, UnicodeError):
        return False
    imports: set[str] = set()
    calls: set[str] = set()
    strings: set[str] = set()
    integer_literals: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0].lower() for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0].lower())
        elif isinstance(node, ast.Call):
            calls.add(dotted_name(node.func).lower().split(".")[-1])
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            strings.add(node.value.lower())
        elif isinstance(node, ast.Constant) and isinstance(node.value, int):
            integer_literals.add(node.value)
    required_calls = {
        "rectanglemesh",
        "submesh",
        "functionspace",
        "dirichletbc",
        "facetnormal",
        "measure",
        "assemble",
    }
    element_api = ({"vectorelement", "finiteelement"}.issubset(calls) or "vectorfunctionspace" in calls)
    variational_api = bool(calls.intersection({"trialfunction", "trialfunctions"})) and bool(calls.intersection({"testfunction", "testfunctions"}))
    solver_api = bool(calls.intersection({"solve", "linearvariationalsolver", "petsckrylovsolver", "lusolver"}))
    return (
        "dolfin" in imports
        and required_calls.issubset(calls)
        and element_api
        and variational_api
        and solver_api
        and 5 in integer_literals
        and any("summary.txt" in value for value in strings)
        and summary_depends_on_surface_force(tree)
    )


def check_task(root: Path) -> bool:
    script = root / "lift_drag.py"
    summary = root / "summary.txt"
    if not script.is_file() or not check_lift_drag_script(script):
        return False

    summary.unlink(missing_ok=True)
    executed = execute_script(root, script.name)
    runtime_required = {
        "rectanglemesh", "submesh", "functionspace", "dirichletbc",
        "facetnormal", "measure", "assemble",
    }
    solver_api = executed.intersection({"solve", "linearvariationalsolver", "petsckrylovsolver", "lusolver"})
    if not runtime_required.issubset(executed) or not solver_api or not is_nonempty_file(summary):
        return False

    vals = parse_floats(read_text(summary))
    if len(vals) < 2:
        return False
    cd, cl = vals[0], vals[1]

    if abs(cd - 3.168223194180756) > 0.5:
        return False
    if abs(cl - (-0.08055826240762723)) > 0.1:
        return False
    return True

def evaluate() -> int:
    root = Path("/home/user/Desktop")
    try:
        ok = check_task(root)
    except Exception:
        ok = False
    return 1 if ok else 0


def main() -> int:
    result = evaluate()
    print("True" if result == 1 else "False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
