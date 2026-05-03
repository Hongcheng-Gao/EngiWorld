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
