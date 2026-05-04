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
