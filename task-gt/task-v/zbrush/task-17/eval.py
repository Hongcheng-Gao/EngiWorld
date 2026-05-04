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
