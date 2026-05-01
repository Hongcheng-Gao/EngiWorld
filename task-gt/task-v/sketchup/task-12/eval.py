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
INIT_MAP = [('prices.csv', 'C:\\Users\\Administrator\\Desktop\\prices.csv'), ('products.dae', 'C:\\Users\\Administrator\\Desktop\\products.dae')]


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
