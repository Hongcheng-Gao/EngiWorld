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
INIT_MAP = [('bad_terrain.dae', 'C:\\Users\\Administrator\\Desktop\\bad_terrain.dae')]


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
