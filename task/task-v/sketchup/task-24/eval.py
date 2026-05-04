from __future__ import annotations

import base64
import importlib.util
import os
import shutil
import tempfile
import zlib
from pathlib import Path


DESKTOP = Path(r'C:\Users\Administrator\Desktop')
BUNDLE = {'_shared/__init__.py': 'eNoDAAAAAAE=', '_shared/common.py': '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', 'eval_inner.py': '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'}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('house.dae', 'C:\\Users\\Administrator\\Desktop\\house.dae')]


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
    local_tmp = runtime_base / "_tmp"
    local_tmp.mkdir(parents=True, exist_ok=True)
    root = runtime_base / ("engiworld_eval_" + uuid.uuid4().hex)
    root.mkdir(parents=True, exist_ok=False)
    old_env = {key: os.environ.get(key) for key in ("TMP", "TEMP", "TMPDIR")}
    old_tempdir = tempfile.tempdir
    old_mkdtemp = tempfile.mkdtemp
    try:
        tmp_path = str(local_tmp.resolve())
        for key in ("TMP", "TEMP", "TMPDIR"):
            os.environ[key] = tmp_path
        tempfile.tempdir = tmp_path
        def _local_mkdtemp(prefix="tmp", suffix="", dir=None):
            base_dir = Path(dir) if dir else local_tmp
            base_dir.mkdir(parents=True, exist_ok=True)
            created = base_dir / f"{prefix}{uuid.uuid4().hex}{suffix}"
            created.mkdir(parents=True, exist_ok=False)
            return str(created)
        tempfile.mkdtemp = _local_mkdtemp
        _materialize_bundle(root)
        module = _load_module(root)
        func = getattr(module, CALL_FUNC)
        args = [_resolve_arg(arg) for arg in CALL_ARGS]
        result = func(*args)
        return _is_pass(result)
    finally:
        tempfile.tempdir = old_tempdir
        tempfile.mkdtemp = old_mkdtemp
        for key, value in old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        shutil.rmtree(root, ignore_errors=True)
if __name__ == "__main__":
    print("True" if _run() else "False")
