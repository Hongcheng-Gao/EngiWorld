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
