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
INIT_MAP = [('params.json', 'C:\\Users\\Administrator\\Desktop\\params.json')]


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
