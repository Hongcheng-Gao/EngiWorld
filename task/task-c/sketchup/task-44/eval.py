from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


DESKTOP = Path('C:\\Users\\Administrator\\Desktop')
BUNDLE = {'eval_inner.py': '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', 'collada.py': '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'}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('flipped.dae', 'C:\\Users\\Administrator\\Desktop/flipped.dae')]


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
