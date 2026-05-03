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
INIT_MAP = [('broken_tex.dae', 'C:\\Users\\Administrator\\Desktop\\broken_tex.dae'), ('textures\\tex_1.png', 'C:\\Users\\Administrator\\Desktop\\textures\\tex_1.png'), ('textures\\tex_2.png', 'C:\\Users\\Administrator\\Desktop\\textures\\tex_2.png'), ('textures\\tex_3.png', 'C:\\Users\\Administrator\\Desktop\\textures\\tex_3.png'), ('textures\\tex_4.png', 'C:\\Users\\Administrator\\Desktop\\textures\\tex_4.png'), ('textures\\tex_5.png', 'C:\\Users\\Administrator\\Desktop\\textures\\tex_5.png')]


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


def _resolve_arg(spec: str):
    if spec == "__DESKTOP_DIR__":
        return str(DESKTOP)
    return spec


def _run() -> bool:
    import uuid

    runtime_base = Path(__file__).resolve().parent / "_runtime"
    runtime_base.mkdir(parents=True, exist_ok=True)
    root = runtime_base / ("engiworld_eval_" + uuid.uuid4().hex)
    root.mkdir(parents=True, exist_ok=False)
    try:
        _materialize_bundle(root)
        module = _load_module(root)
        func = getattr(module, CALL_FUNC)
        args = [_resolve_arg(arg) for arg in CALL_ARGS]
        result = func(*args)
        return _is_pass(result)
    finally:
        shutil.rmtree(root, ignore_errors=True)
if __name__ == "__main__":
    print("true" if _run() else "false")
