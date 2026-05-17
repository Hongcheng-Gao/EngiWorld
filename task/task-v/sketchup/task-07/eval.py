from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


DESKTOP = Path(r'C:\Users\Administrator\Desktop')
BUNDLE = {'eval_inner.py': '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'}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = []


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



def _has_generated_python_file() -> bool:
    if not DESKTOP.exists():
        return False
    initial_python_names = {Path(rel).name for rel, _ in INIT_MAP if Path(rel).suffix.lower() == ".py"}
    allowed_names = {"eval.py"}
    allowed_names.update(initial_python_names)
    try:
        items = list(DESKTOP.iterdir())
    except Exception:
        return False
    for path in items:
        if path.name in allowed_names or path.name == "_runtime":
            continue
        try:
            if path.is_file() and path.suffix.lower() == ".py":
                return True
        except Exception:
            continue
    return False

def _run() -> bool:
    if _has_generated_python_file():
        return False

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
    finally:
        shutil.rmtree(root, ignore_errors=True)
if __name__ == "__main__":
    print("True" if _run() else "False")
