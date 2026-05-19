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
