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
CALL_ARGS = ['C:\\Users\\Administrator\\Desktop\\animated.abc']
INIT_MAP = [('scene.blend', 'C:\\Users\\Administrator\\Desktop\\scene.blend'), ('stub.abc', 'C:\\Users\\Administrator\\Desktop\\stub.abc')]


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
