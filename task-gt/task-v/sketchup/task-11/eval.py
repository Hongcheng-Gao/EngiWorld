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
    except Exception:
        return False
    finally:
        shutil.rmtree(root, ignore_errors=True)
if __name__ == "__main__":
    print("true" if _run() else "false")
