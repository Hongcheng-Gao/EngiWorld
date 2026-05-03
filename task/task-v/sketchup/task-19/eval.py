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
    print("true" if _run() else "false")
