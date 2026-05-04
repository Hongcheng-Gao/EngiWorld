from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


DESKTOP = Path('C:\\Users\\Administrator\\Desktop')
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
    print("True" if _run() else "False")
