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
INIT_MAP = [('tex\\brick.png', 'C:\\Users\\Administrator\\Desktop\\tex\\brick.png')]


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
