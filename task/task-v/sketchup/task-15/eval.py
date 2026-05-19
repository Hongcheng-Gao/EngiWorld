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
