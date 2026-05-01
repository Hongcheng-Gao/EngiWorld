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
INIT_MAP = [('spiral_spec.json', 'C:\\Users\\Administrator\\Desktop\\spiral_spec.json')]


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
