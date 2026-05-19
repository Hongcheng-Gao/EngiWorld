from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


DESKTOP = Path(r'C:\Users\user\Desktop')
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
