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
