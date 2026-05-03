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
