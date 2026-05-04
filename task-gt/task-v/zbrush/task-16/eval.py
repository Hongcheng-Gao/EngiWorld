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
