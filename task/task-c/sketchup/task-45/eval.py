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
INIT_MAP = [('loose.dae', 'C:\\Users\\Administrator\\Desktop/loose.dae')]


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
