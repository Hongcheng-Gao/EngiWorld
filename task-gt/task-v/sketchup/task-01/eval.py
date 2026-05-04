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
    finally:
        shutil.rmtree(root, ignore_errors=True)
if __name__ == "__main__":
    print("True" if _run() else "False")
