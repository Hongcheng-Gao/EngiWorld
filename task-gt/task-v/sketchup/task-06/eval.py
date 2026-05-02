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
    except Exception:
        return False
    finally:
        shutil.rmtree(root, ignore_errors=True)
if __name__ == "__main__":
    print("true" if _run() else "false")
