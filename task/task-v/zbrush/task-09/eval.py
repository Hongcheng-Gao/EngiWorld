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
