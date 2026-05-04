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
