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
CALL_ARGS = ['C:\\Users\\Administrator\\Desktop\\output.obj']
INIT_MAP = [('scene.obj', 'C:\\Users\\Administrator\\Desktop\\scene.obj')]


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
