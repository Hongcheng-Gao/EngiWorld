#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import concurrent.futures
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

    def target_names(target: ast.AST) -> list[str]:
        if isinstance(target, ast.Name):
            return [target.id]
        if isinstance(target, (ast.Tuple, ast.List)):
            return [name for item in target.elts for name in target_names(item)]
        return []

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                for name in target_names(target):
                    assignments.setdefault(name, []).append(node.value)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.value is not None:
            assignments.setdefault(node.target.id, []).append(node.value)
    return assignments


def expression_dependencies(
    node: ast.AST,
    assignments: dict[str, list[ast.AST]],
    function_dependencies: dict[str, set[str]],
    seen: set[str] | None = None,
) -> set[str]:
    seen = set() if seen is None else seen
    dependencies: set[str] = set()
    if isinstance(node, ast.Name):
        if node.id in seen:
            return dependencies
        for value in assignments.get(node.id, []):
            dependencies.update(expression_dependencies(value, assignments, function_dependencies, seen | {node.id}))
        return dependencies
    if isinstance(node, ast.Call):
        call_name = dotted_name(node.func).lower().split(".")[-1]
        dependencies.add(call_name)
        dependencies.update(function_dependencies.get(call_name, set()))
        dependencies.update(expression_dependencies(node.func, assignments, function_dependencies, seen))
        for argument in node.args:
            dependencies.update(expression_dependencies(argument, assignments, function_dependencies, seen))
        for keyword in node.keywords:
            dependencies.update(expression_dependencies(keyword.value, assignments, function_dependencies, seen))
        return dependencies
    for child in ast.iter_child_nodes(node):
        dependencies.update(expression_dependencies(child, assignments, function_dependencies, seen))
    return dependencies


def returned_function_dependencies(tree: ast.AST) -> dict[str, set[str]]:
    results: dict[str, set[str]] = {}
    functions = [node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
    for _ in range(max(1, len(functions))):
        changed = False
        for function in functions:
            assignments = assignment_expressions(function)
            dependencies: set[str] = set()
            for node in ast.walk(function):
                if isinstance(node, ast.Return) and node.value is not None:
                    dependencies.update(expression_dependencies(node.value, assignments, results))
            key = function.name.lower()
            if dependencies != results.get(key, set()):
                results[key] = dependencies
                changed = True
        if not changed:
            break
    return results


def result_depends_on_cavity_solution(tree: ast.AST, external_functions: dict[str, set[str]]) -> bool:
    functions = dict(external_functions)
    functions.update(returned_function_dependencies(tree))
    assignments = assignment_expressions(tree)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or dotted_name(node.func).lower().split(".")[-1] not in {"write", "write_text"}:
            continue
        if node.args:
            dependencies = expression_dependencies(node.args[0], assignments, functions)
            if "point" in dependencies and dependencies.intersection({"split", "sub", "function"}):
                return True
    return False


def execute_workflow(root: Path, entry_name: str, target_names: list[str], timeout: int) -> dict[str, set[str]]:
    with tempfile.TemporaryDirectory(prefix="fenics-task13-eval-") as temp_dir:
        runner = Path(temp_dir) / "runner.py"
        runner.write_bytes(__import__("zlib").decompress(__import__("base64").b64decode(PRIVATE_RUNNER_B64)))
        sources = [str((root / entry_name).resolve())]
        sources.extend(str((root / name).resolve()) for name in target_names if name != entry_name)
        completed = subprocess.run(
            [sys.executable, str(runner), *sources], cwd=root,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=timeout,
        )
        if completed.returncode != 0:
            raise ValueError("the cavity workflow did not complete successfully")
        marker = "__EVAL_PRIVATE_CALLS__"
        if marker not in completed.stdout:
            raise ValueError("the cavity workflow produced no private execution evidence")
        evidence = json.loads(completed.stdout.rsplit(marker, 1)[1].splitlines()[0])
    return {name: set(evidence.get(name, [])) for name in target_names}


def check_common_solver(path: Path) -> bool:
    try:
        tree = ast.parse(read_text(path), filename=path.name)
    except (OSError, SyntaxError, UnicodeError):
        return False
    imports: set[str] = set()
    calls: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0].lower() for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0].lower())
        elif isinstance(node, ast.Call):
            calls.add(dotted_name(node.func).lower().split(".")[-1])
    core = {"unitsquaremesh", "functionspace", "dirichletbc", "point"}
    element_api = ({"vectorelement", "finiteelement"}.issubset(calls) or "vectorfunctionspace" in calls)
    variational_api = bool(calls.intersection({"trialfunction", "trialfunctions"})) and bool(calls.intersection({"testfunction", "testfunctions"}))
    solver_api = bool(calls.intersection({"solve", "linearvariationalsolver", "petsckrylovsolver", "lusolver"}))
    return "dolfin" in imports and core.issubset(calls) and element_api and variational_api and solver_api


def check_case_script(path: Path, reynolds: int, external_functions: dict[str, set[str]]) -> bool:
    try:
        source = read_text(path)
        tree = ast.parse(source, filename=path.name)
    except (OSError, SyntaxError, UnicodeError):
        return False
    numeric_literals = {
        int(node.value) for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and float(node.value).is_integer()
    }
    return (
        reynolds in numeric_literals
        and f"re_{reynolds}.result" in source
        and result_depends_on_cavity_solution(tree, external_functions)
    )


def check_task(root: Path) -> bool:
    source_files = [
        "re_100.py",
        "re_400.py",
        "re_1000.py",
        "summarize.py",
    ]
    for rel in source_files:
        if not (root / rel).is_file():
            return False
    shared_solver = (root / "cavity_common.py").is_file()
    if shared_solver and not check_common_solver(root / "cavity_common.py"):
        return False
    shared_functions: dict[str, set[str]] = {}
    if shared_solver:
        try:
            shared_tree = ast.parse(read_text(root / "cavity_common.py"), filename="cavity_common.py")
        except (OSError, SyntaxError, UnicodeError):
            return False
        shared_functions = returned_function_dependencies(shared_tree)
    for reynolds in (100, 400, 1000):
        if not check_case_script(root / f"re_{reynolds}.py", reynolds, shared_functions):
            return False
        if not shared_solver and not check_common_solver(root / f"re_{reynolds}.py"):
            return False
    summarize_source = read_text(root / "summarize.py")
    if "summary.txt" not in summarize_source or ".result" not in summarize_source:
        return False

    for artifact in ("re_100.result", "re_400.result", "re_1000.result", "summary.txt"):
        (root / artifact).unlink(missing_ok=True)
    case_calls: dict[int, dict[str, set[str]]] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        pending = {
            reynolds: executor.submit(
                execute_workflow,
                root,
                f"re_{reynolds}.py",
                ([f"re_{reynolds}.py", "cavity_common.py"] if shared_solver else [f"re_{reynolds}.py"]),
                105,
            )
            for reynolds in (100, 400, 1000)
        }
        for reynolds, future in pending.items():
            case_calls[reynolds] = future.result()

    solver_calls: list[set[str]] = []
    for reynolds, calls_by_file in case_calls.items():
        case_name = f"re_{reynolds}.py"
        solver_calls.append(calls_by_file["cavity_common.py"] if shared_solver else calls_by_file[case_name])
    runtime_core = {"unitsquaremesh", "functionspace", "dirichletbc", "point"}
    if any(not runtime_core.issubset(calls) or not calls.intersection({"solve", "linearvariationalsolver", "petsckrylovsolver", "lusolver"}) for calls in solver_calls):
        return False

    summarize_calls = execute_workflow(root, "summarize.py", ["summarize.py"], 15)["summarize.py"]
    if not {"read_text", "write_text"}.issubset(summarize_calls):
        return False

    result_files: dict[int, float] = {}
    for reynolds in (100, 400, 1000):
        result_path = root / f"re_{reynolds}.result"
        if not is_nonempty_file(result_path):
            return False
        result_values = parse_floats(read_text(result_path))
        if len(result_values) < 2 or int(round(result_values[0])) != reynolds:
            return False
        result_files[reynolds] = result_values[1]
    if not is_nonempty_file(root / "summary.txt"):
        return False

    results: dict[int, float] = {}
    for raw_line in read_text(root / "summary.txt").splitlines():
        line = raw_line.strip()
        if (not line) or line.startswith("#"):
            continue
        vals = parse_floats(line)
        if len(vals) < 2:
            continue
        re_float, ux = vals[0], vals[1]
        re_int = int(round(re_float))
        if abs(re_float - re_int) > 1e-6:
            continue
        results[re_int] = ux

    for re_val in (100, 400, 1000):
        if re_val not in results:
            return False
        if not abs(results[re_val] - result_files[re_val]) <= 1.0e-12:
            return False

    expected = {
        100: -0.2091295638382351,
        400: -0.1149858626712449,
        1000: -0.06187004148288549,
    }
    for reynolds, target in expected.items():
        if abs(results[reynolds] - target) > 0.025:
            return False
    if not (results[100] < results[400] < results[1000] < 0.0):
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
