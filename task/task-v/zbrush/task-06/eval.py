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


def _materialize_desktop_view(root: Path) -> Path:
    stage = root / "_desktop_view"
    stage.mkdir(parents=True, exist_ok=True)
    if DESKTOP.exists():
        for item in DESKTOP.iterdir():
            if item.name in {"eval.py", "_runtime"}:
                continue
            dst = stage / item.name
            if item.is_dir():
                shutil.copytree(item, dst, dirs_exist_ok=True)
            elif item.is_file():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, dst)
    for rel, desktop_path in INIT_MAP:
        src = Path(desktop_path)
        if src.exists():
            dst = stage / "initial_files" / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    return stage


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


def _resolve_arg(spec: str, desktop_view: Path):
    if spec == "__DESKTOP_DIR__":
        return str(desktop_view)
    desktop_prefix = str(DESKTOP)
    if spec.startswith(desktop_prefix):
        rel = spec[len(desktop_prefix):].lstrip("\\/")
        return str(desktop_view / Path(rel)) if rel else str(desktop_view)
    return spec



def _has_generated_python_file() -> bool:
    if not DESKTOP.exists():
        return False
    initial_python_names = {Path(rel).name for rel, _ in INIT_MAP if Path(rel).suffix.lower() == ".py"}
    allowed_names = {"eval.py"}
    allowed_names.update(initial_python_names)
    try:
        items = list(DESKTOP.iterdir())
    except Exception:
        return False
    for path in items:
        if path.name in allowed_names or path.name == "_runtime":
            continue
        try:
            if path.is_file() and path.suffix.lower() == ".py":
                return True
        except Exception:
            continue
    return False

def _run() -> bool:
    if _has_generated_python_file():
        return False

    import uuid

    runtime_base = Path(__file__).resolve().parent / "_runtime"
    runtime_base.mkdir(parents=True, exist_ok=True)
    root = runtime_base / ("engiworld_eval_" + uuid.uuid4().hex)
    root.mkdir(parents=True, exist_ok=False)
    try:
        _materialize_bundle(root)
        desktop_view = _materialize_desktop_view(root)
        module = _load_module(root)
        func = getattr(module, CALL_FUNC)
        args = [_resolve_arg(arg, desktop_view) for arg in CALL_ARGS]
        result = func(*args)
        return _is_pass(result)
    except Exception:
        return False
    finally:
        shutil.rmtree(root, ignore_errors=True)
if __name__ == "__main__":
    print("True" if _run() else "False")
