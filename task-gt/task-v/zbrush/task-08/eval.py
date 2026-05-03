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
