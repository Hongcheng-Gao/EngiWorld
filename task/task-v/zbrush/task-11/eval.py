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
