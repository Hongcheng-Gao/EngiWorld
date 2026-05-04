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
