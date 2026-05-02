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
INIT_MAP = [('spec.json', 'C:\\Users\\Administrator\\Desktop/spec.json')]


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
