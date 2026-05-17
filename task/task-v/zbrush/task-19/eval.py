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
