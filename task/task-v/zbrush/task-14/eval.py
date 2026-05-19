from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


DESKTOP = Path(r'C:\Users\user\Desktop')
BUNDLE = {'eval_inner.py': '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'}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('scene.obj', 'C:\\Users\\user\\Desktop\\scene.obj')]


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
