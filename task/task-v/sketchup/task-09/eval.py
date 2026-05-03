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
    print("true" if _run() else "false")
