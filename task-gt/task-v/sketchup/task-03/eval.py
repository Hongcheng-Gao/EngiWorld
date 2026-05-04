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
