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
    print("true" if _run() else "false")
