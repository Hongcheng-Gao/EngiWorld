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
