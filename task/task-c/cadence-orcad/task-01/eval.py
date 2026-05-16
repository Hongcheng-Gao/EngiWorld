from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


DESKTOP = Path('/home/user/Desktop')
BUNDLE = {'eval_inner.py': 'eNqNVc1u3DYQvvMpJuxFKrxK0lOxqAI4QNocjcLtxTG4XGkksdaSAkmlaxgG+hB9wj5Jh6S0K9mJkz2Jw29mvvnZj5xz/Cz7YriHxljw0t1t3ryF//75Fw5oW4QanWq1kCB1PR/2YLGhb+iV865g7E+0qlFk8J30sDOjH0YvamVfxyC1SPjCH/1uywB+hMpoL5V2gLLqAI8DVh5r2F1ufyHsu11Mt3s/n/AoK9/fg9EVRv9eaUonLYIzljy3cLmFfW+qO9gjVYLwfjpfgOyHTm4SDvb3M/m/le+UZpxz1lhzACGa0Y8WhQB1GAhNHLTx0iujHWOT7S9n9Pzt7l1yHaTverWf/a7oyNjHD79/gDIeMoqteoqcFxad6T9jlhcDsdee/QB/OITWmpEq9nb0HQQsSAdO6bYPFY62QjBNuma/XYury+uPFDumeA08eYt4zYPhWds5Y6zGBkRvZC1i97JhG8nlsHkXJ3njvL0N4wFQDVDpMBR4DCPO8mQOP4vUJA03t2x5ChELSwHUkPFP9pPmeVyoYAelKZJFSuzx6DPUlamptJKPvtn8zPPCDb3yiVQecsdoKVh+OzEPayrSZrnsvGGRfa0qnxieL+bWL6Dn5kespPUrlx5fblwqMw62hAc+SOf4Fn6VvcML4Gd3MhLlZb7HZS8p2xe7GQLfcOoOLRa/pRQNPygXRr+FB3J65E9bn3xYNJ/+OeVqtNOKpDpb459cU9icLdPPYURFi+QjjR51NpvXYIr3BEeWnC2LnR2/Uag268Un8XiYqL9cNqVx6GNeeFXG7xPXc86pj5Qq/fmzFQ42pxj5yYX208q1Q0yyWefIX6qLEzTkPkhfdfwZcmIVodP3M0ykERHx6xutCAN+VX5f07mxNdoTPchOuuk6M/Y1DBYrrL+qn6TZqsb8xenMaeNfJSS9tiOubqoOq7t0d3OK1HDZ9/CwWrzHWa1JKm14YRLr1dbMj0OmdNWPQVkgFjmRXAnVTJNR24TQ8hDkvqS2CHGg90gIPgng9ALYlmTaJfJyILqzpbi07XggVlfhZGdJGQpZ10JOd9lSHiaEbYPqEDCGCVA3OQfJWqlcuCsWehJRg1UUODxDRT0eBpfZCxpKTdnKny6oTS48YdJVSpVRo6ZdpbcqyI/P3oSNsUVL65wGlAMSDN7m7H/MY5rL', 'ground_truth/merged_refdes.txt': 'eNplzL0KgCAAReE96F1Sb39u+g7OIkg09P5z1iEQWu7HXU7wyU3jEBoGLDgQzLDAChvsL6IiKqIiKqIiKqIiKqKiVon+LNdRas2hP/E5yXRrf+u+vQGk5ynS'}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('design_a.DSN', '/home/user/Desktop/design_a.DSN'), ('design_a.OPJ', '/home/user/Desktop/design_a.OPJ'), ('design_b.DSN', '/home/user/Desktop/design_b.DSN'), ('design_b.OPJ', '/home/user/Desktop/design_b.OPJ')]


def _decode(payload: str) -> bytes:
    return zlib.decompress(base64.b64decode(payload.encode("ascii")))


def _materialize_bundle(root: Path) -> None:
    for rel, payload in BUNDLE.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(_decode(payload))
    for dirname in ("init_file", "ground_truth", "_internal"):
        (root / dirname).mkdir(parents=True, exist_ok=True)
    for rel, desktop_path in INIT_MAP:
        src = Path(desktop_path)
        dst = root / "init_file" / rel
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)


def _bundle_python_paths(root: Path) -> list[str]:
    paths: list[str] = []
    seen: set[str] = set()

    def add(path: Path) -> None:
        text = str(path)
        if text not in seen:
            seen.add(text)
            paths.append(text)

    add(root)
    for rel in BUNDLE:
        rel_path = Path(rel)
        if rel_path.suffix == ".py" and rel_path.parent != Path("."):
            add(root / rel_path.parent)
    return paths



def _load_module(root: Path):
    spec = importlib.util.spec_from_file_location("eval_inner", root / "eval_inner.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load eval_inner.py")
    module = importlib.util.module_from_spec(spec)
    import sys

    sys.modules["eval_inner"] = module
    added_paths = _bundle_python_paths(root)
    for path in reversed(added_paths):
        sys.path.insert(0, path)
    try:
        spec.loader.exec_module(module)
    finally:
        for path in added_paths:
            try:
                sys.path.remove(path)
            except ValueError:
                pass
    return module
def _is_pass(result) -> bool:
    if isinstance(result, bool):
        return result
    if isinstance(result, dict):
        if "pass" in result:
            return bool(result["pass"])
        if "passed" in result:
            return bool(result["passed"])
        score = result.get("score")
        if isinstance(score, (int, float)):
            return float(score) == 1.0
    for attr in ("all_passed", "passed"):
        if hasattr(result, attr):
            value = getattr(result, attr)
            if isinstance(value, bool):
                return value
    if hasattr(result, "score"):
        try:
            return float(getattr(result, "score")) == 1.0
        except Exception:
            pass
    return False


def _resolve_arg(spec: str):
    if spec == "__DESKTOP_DIR__":
        return str(DESKTOP)
    return spec


def _run() -> bool:
    import uuid

    runtime_base = Path(__file__).resolve().parent / "_runtime"
    runtime_base.mkdir(parents=True, exist_ok=True)
    root = runtime_base / ("engiworld_eval_" + uuid.uuid4().hex)
    root.mkdir(parents=True, exist_ok=False)
    try:
        _materialize_bundle(root)
        module = _load_module(root)
        func = getattr(module, CALL_FUNC)
        args = [_resolve_arg(arg) for arg in CALL_ARGS]
        result = func(*args)
        return _is_pass(result)
    except Exception:
        return False
    finally:
        shutil.rmtree(root, ignore_errors=True)
if __name__ == "__main__":
    print("true" if _run() else "false")
