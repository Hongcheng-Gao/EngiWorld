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


def execute_script(root: Path, filename: str, timeout: int = 180) -> list[str]:
    script = (root / filename).resolve()
    with tempfile.TemporaryDirectory(prefix="fenics-task12-eval-") as temp_dir:
        runner = Path(temp_dir) / "runner.py"
        runner.write_bytes(__import__("zlib").decompress(__import__("base64").b64decode(PRIVATE_RUNNER_B64)))
        completed = subprocess.run(
            [sys.executable, str(runner), str(script)], cwd=root,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=timeout,
        )
        if completed.returncode != 0:
            raise ValueError("thermomech.py did not complete successfully")
        marker = "__EVAL_PRIVATE_CALLS__"
        if marker not in completed.stdout:
            raise ValueError("thermomech.py produced no private execution evidence")
        evidence = json.loads(completed.stdout.rsplit(marker, 1)[1].splitlines()[0])
    return list(evidence.get(filename, []))


def check_thermomech_script(path: Path) -> bool:
    try:
        source = read_text(path)
        tree = ast.parse(source, filename=path.name)
    except (OSError, SyntaxError, UnicodeError):
        return False
    imports: set[str] = set()
    calls: list[str] = []
    strings: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0].lower() for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0].lower())
        elif isinstance(node, ast.Call):
            calls.append(dotted_name(node.func).lower().split(".")[-1])
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            strings.add(node.value.lower())
    required_calls = {
        "rectanglemesh",
        "functionspace",
        "vectorfunctionspace",
        "dirichletbc",
        "trialfunction",
        "testfunction",
        "solve",
        "sym",
        "grad",
        "tr",
        "identity",
        "project",
    }
    return (
        "dolfin" in imports
        and required_calls.issubset(set(calls))
        and calls.count("solve") >= 2
        and any("summary.txt" in value for value in strings)
        and "1.2e-5" in source
        and "210000" in source
        and "0.3" in source
    )


def check_task(root: Path) -> bool:
    script = root / "thermomech.py"
    summary = root / "summary.txt"
    if not script.is_file() or not check_thermomech_script(script):
        return False

    summary.unlink(missing_ok=True)
    executed_calls = execute_script(root, script.name)
    runtime_required = {
        "rectanglemesh", "functionspace", "vectorfunctionspace",
        "dirichletbc", "solve", "project",
    }
    if (
        not runtime_required.issubset(set(executed_calls))
        or executed_calls.count("solve") < 2
        or not is_nonempty_file(summary)
    ):
        return False

    vals = parse_floats(read_text(summary))
    if len(vals) < 2:
        return False
    mises, ux = vals[0], vals[1]

    if mises <= 0.0:
        return False
    if abs(mises - 189.6033446245451) > 19.0:
        return False
    if abs(ux - 0.01309290213912474) > 0.003:
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
