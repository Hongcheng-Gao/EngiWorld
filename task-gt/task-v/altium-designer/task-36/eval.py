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
INIT_MAP = [('spec.yaml', 'C:\\Users\\Administrator\\Desktop\\spec.yaml'), ('template.OutJob', 'C:\\Users\\Administrator\\Desktop\\template.OutJob')]


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
