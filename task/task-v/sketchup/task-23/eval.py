from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


DESKTOP = Path(r'C:\Users\user\Desktop')
BUNDLE = {'_shared/__init__.py': 'eNoDAAAAAAE=', '_shared/common.py': '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', 'eval_inner.py': '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'}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('house.dae', 'C:\\Users\\user\\Desktop\\house.dae')]


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
