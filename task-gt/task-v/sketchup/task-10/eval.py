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
