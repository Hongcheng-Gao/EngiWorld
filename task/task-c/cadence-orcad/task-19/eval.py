from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


DESKTOP = Path('/home/user/Desktop')
BUNDLE = {'eval_inner.py': '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', 'ground_truth/mixed.json': 'eNqr5uVSUFAqUbJSMEzVNdYB8wKBPCUPTyUoz8kxCCTg4w8VCIsHKTDRszSC8yFKDPQMLHi5anm5AJ0YD6k=', 'ground_truth/mixed.out': 'eNqtkF1LwzAYhe8L/Q+HXemkWRLr5gpeZG3QStPWJhVEZIhWCGxW/MKfb9IVnfcechPy5LxPEgaYugC1frEPHcQsA1uQmFAclP0nOOX8EBGU/eoeoe32Y3P/bvtnjNfAlkkcJ+wEoPGMuzUPg9CXon7tn+ymSzDR6YVUwuQpi0wjyglusfV95M1ucef5cNTwxzqXpYEoRXGjc42fGKlq2QjTNhJnbs8XhFKKTJ4j3XVM/zX7Xi5KCu1GKy/XSN0WRo8ErtbCrJn6dfV6MVly5yePnKPL9QCuRPOH9eCpf4YDI8pHcGi9rFZIqzIt2kxmuznjP1RGFMOxyZXEfuaEHYfBN4lNXfo='}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('mixed.cir', '/home/user/Desktop/mixed.cir')]


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
