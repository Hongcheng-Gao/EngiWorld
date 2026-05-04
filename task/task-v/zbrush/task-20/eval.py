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
