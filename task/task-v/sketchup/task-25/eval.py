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
INIT_MAP = [('house.dae', 'C:\\Users\\Administrator\\Desktop\\house.dae')]


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
