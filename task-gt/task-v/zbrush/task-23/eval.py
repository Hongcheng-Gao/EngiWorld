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


def _run() -> bool:
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
