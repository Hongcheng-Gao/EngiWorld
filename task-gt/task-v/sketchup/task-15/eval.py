from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


DESKTOP = Path(r'C:\Users\Administrator\Desktop')
BUNDLE = {'_shared/__init__.py': 'eNoDAAAAAAE=', '_shared/common.py': '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', 'eval_inner.py': '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'}
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
