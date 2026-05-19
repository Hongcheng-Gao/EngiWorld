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
