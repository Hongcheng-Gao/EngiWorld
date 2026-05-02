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
