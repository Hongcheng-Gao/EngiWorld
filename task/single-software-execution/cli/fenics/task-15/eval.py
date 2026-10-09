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
PRIVATE_RUNNER = r'''
import ast, dis, json, secrets, sys, types
from pathlib import Path

MARKER = "__EVAL_PRIVATE_CALLS__"

def dotted_name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = dotted_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""

def code_objects(code):
    yield code
    for value in code.co_consts:
        if isinstance(value, type(code)):
            yield from code_objects(value)

def main():
    paths = [Path(arg).resolve() for arg in sys.argv[1:]]
    token = secrets.token_hex(16)
    compiled = {}
    call_names = {}
    helper_nodes = {}
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        names = {}
        class Instrument(ast.NodeTransformer):
            def visit_ClassDef(self, node):
                return node

            def visit_Call(self, node):
                self.generic_visit(node)
                node_id = f"{path.name}:{node.lineno}:{node.col_offset}:{len(names)}"
                helper = f"__ev_{token}_{len(helper_nodes)}"
                names[node_id] = dotted_name(node.func).lower().split(".")[-1]
                helper_nodes[helper] = (path.name, node_id)
                factory = ast.Call(ast.Name(helper, ast.Load()), [], [])
                return ast.copy_location(ast.Call(factory, [node], []), node)
        tree = Instrument().visit(tree)
        ast.fix_missing_locations(tree)
        compiled[path.name] = compile(tree, str(path), "exec")
        call_names[path.name] = names

    allowed = {name: set() for name in helper_nodes}
    for code in compiled.values():
        for child in code_objects(code):
            instructions = list(dis.get_instructions(child))
            for index, instruction in enumerate(instructions):
                if instruction.opname.startswith("LOAD_") and instruction.argval in allowed:
                    for candidate in instructions[index + 1:index + 6]:
                        if "CALL" in candidate.opname and not candidate.opname.startswith("PRECALL"):
                            allowed[instruction.argval].add((child, candidate.offset))
                            break

    executed = {path.name: [] for path in paths}
    bindings = {}
    for helper, (filename, node_id) in helper_nodes.items():
        def make_factory(helper_name=helper, source_name=filename, call_id=node_id):
            def factory():
                caller = sys._getframe(1)
                valid = any(caller.f_code is code and caller.f_lasti == offset for code, offset in allowed[helper_name])
                def record(value):
                    if valid:
                        executed[source_name].append(call_id)
                    return value
                return record
            return factory
        bindings[helper] = make_factory()

    def namespace(path, module_name):
        return {"__name__": module_name, "__file__": str(path), **bindings}

    entry = paths[0]
    for dependency in paths[1:]:
        module = types.ModuleType(dependency.stem)
        module.__dict__.update(namespace(dependency, dependency.stem))
        sys.modules[dependency.stem] = module
        exec(compiled[dependency.name], module.__dict__)
    try:
        exec(compiled[entry.name], namespace(entry, "__main__"))
    except SystemExit as exc:
        if exc.code not in (None, 0):
            raise
    result = {
        filename: [call_names[filename][node_id] for node_id in node_ids]
        for filename, node_ids in executed.items()
    }
    print(MARKER + json.dumps(result, sort_keys=True))

main()
'''


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


def summary_depends_on_hyperelastic_outputs(tree: ast.AST) -> bool:
    assignments = assignment_expressions(tree)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or dotted_name(node.func).lower().split(".")[-1] not in {"write", "write_text"}:
            continue
        if node.args:
            dependencies = expression_dependencies(node.args[0], assignments)
            if {"assemble", "max"}.issubset(dependencies) and dependencies.intersection({"project", "interpolate"}):
                return True
    return False


def execute_script(root: Path, filename: str, timeout: int = 240) -> set[str]:
    script = (root / filename).resolve()
    with tempfile.TemporaryDirectory(prefix="fenics-task15-eval-") as temp_dir:
        runner = Path(temp_dir) / "runner.py"
        runner.write_text(PRIVATE_RUNNER, encoding="utf-8")
        completed = subprocess.run(
            [sys.executable, str(runner), str(script)], cwd=root,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=timeout,
        )
        if completed.returncode != 0:
            raise ValueError("hyper.py did not complete successfully")
        marker = "__EVAL_PRIVATE_CALLS__"
        if marker not in completed.stdout:
            raise ValueError("hyper.py produced no private execution evidence")
        evidence = json.loads(completed.stdout.rsplit(marker, 1)[1].splitlines()[0])
    return set(evidence.get(filename, []))


def check_hyperelastic_script(path: Path) -> bool:
    try:
        source = read_text(path)
        tree = ast.parse(source, filename=path.name)
    except (OSError, SyntaxError, UnicodeError):
        return False
    imports: set[str] = set()
    calls: set[str] = set()
    strings: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0].lower() for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0].lower())
        elif isinstance(node, ast.Call):
            calls.add(dotted_name(node.func).lower().split(".")[-1])
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            strings.add(node.value.lower())
    required_calls = {
        "boxmesh",
        "vectorfunctionspace",
        "dirichletbc",
        "identity",
        "grad",
        "tr",
        "det",
        "ln",
        "derivative",
        "nonlinearvariationalproblem",
        "nonlinearvariationalsolver",
        "solve",
        "assemble",
        "project",
    }
    return (
        "dolfin" in imports
        and required_calls.issubset(calls)
        and any("summary.txt" in value for value in strings)
        and summary_depends_on_hyperelastic_outputs(tree)
    )


def check_task(root: Path) -> bool:
    script = root / "hyper.py"
    summary = root / "summary.txt"
    if not script.is_file() or not check_hyperelastic_script(script):
        return False

    summary.unlink(missing_ok=True)
    executed = execute_script(root, script.name)
    runtime_required = {
        "boxmesh", "vectorfunctionspace", "dirichletbc",
        "derivative", "nonlinearvariationalproblem", "nonlinearvariationalsolver",
        "solve", "assemble", "project",
    }
    if not runtime_required.issubset(executed) or not is_nonempty_file(summary):
        return False

    vals = parse_floats(read_text(summary))
    if len(vals) < 2:
        return False
    rx, strain = vals[0], vals[1]

    if rx >= 0.0:
        return False
    if strain <= 0.0:
        return False
    if abs(rx - (-9020.398258602991)) > 902.1:
        return False
    if abs(strain - 0.6653498504563046) > 0.07:
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
