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
INIT_MAP = [('stackup.json', 'C:\\Users\\Administrator\\Desktop\\stackup.json'), ('template.OutJob', 'C:\\Users\\Administrator\\Desktop\\template.OutJob')]


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
