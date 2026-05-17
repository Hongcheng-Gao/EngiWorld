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
