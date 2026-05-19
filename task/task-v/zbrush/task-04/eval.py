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
CALL_ARGS = ['C:\\Users\\user\\Desktop\\output.obj']
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
