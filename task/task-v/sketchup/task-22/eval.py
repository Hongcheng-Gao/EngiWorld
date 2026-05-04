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
