from __future__ import annotations

import base64
import importlib.util
import json
import subprocess
import shutil
import zlib
from pathlib import Path


DESKTOP = Path('/home/user/Desktop')
BLENDER_PATH = "blender"

BUNDLE = {'eval_inner.py': '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'}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['/home/user/Desktop/output/clean.obj']
INIT_MAP = [('scan.obj', '/home/user/Desktop/scan.obj')]


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
        if "all_passed" in result:
            return bool(result["all_passed"])
        score = result.get("score", result.get("total_score"))
        if isinstance(score, (int, float)):
            return float(score) == 1.0
    for attr in ("all_passed", "passed"):
        if hasattr(result, attr):
            value = getattr(result, attr)
            if isinstance(value, bool):
                return value
    for attr in ("score", "total_score"):
        if hasattr(result, attr):
            try:
                return float(getattr(result, attr)) == 1.0
            except Exception:
                pass
    return False


def _resolve_arg(spec: str):
    if spec == "__DESKTOP_DIR__":
        return str(DESKTOP)
    desktop_prefix = "/home/user/Desktop"
    if spec.startswith(desktop_prefix):
        rel = spec[len(desktop_prefix):].lstrip("/")
        return str(DESKTOP / rel) if rel else str(DESKTOP)
    return spec


def _call_inner(root: Path):
    module = _load_module(root)
    func = getattr(module, CALL_FUNC)
    args = [_resolve_arg(arg) for arg in CALL_ARGS]
    return func(*args)


def _have_bpy() -> bool:
    try:
        import bpy  # noqa: F401
        return True
    except Exception:
        return False


def _run_via_blender(root: Path) -> bool:
    result_path = root / "_blender_result.json"
    runner_path = root / "_blender_runner.py"
    added_paths = _bundle_python_paths(root)
    args = [_resolve_arg(arg) for arg in CALL_ARGS]
    runner_code = f"""
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path({str(root)!r})
RESULT_PATH = Path({str(result_path)!r})
CALL_FUNC = {CALL_FUNC!r}
CALL_ARGS = {args!r}
ADDED_PATHS = {added_paths!r}


def _is_pass(result):
    if isinstance(result, bool):
        return result
    if isinstance(result, dict):
        if "pass" in result:
            return bool(result["pass"])
        if "passed" in result:
            return bool(result["passed"])
        if "all_passed" in result:
            return bool(result["all_passed"])
        score = result.get("score", result.get("total_score"))
        if isinstance(score, (int, float)):
            return float(score) == 1.0
    for attr in ("all_passed", "passed"):
        if hasattr(result, attr):
            value = getattr(result, attr)
            if isinstance(value, bool):
                return value
    for attr in ("score", "total_score"):
        if hasattr(result, attr):
            try:
                return float(getattr(result, attr)) == 1.0
            except Exception:
                pass
    return False


spec = importlib.util.spec_from_file_location("eval_inner", ROOT / "eval_inner.py")
if spec is None or spec.loader is None:
    raise RuntimeError("unable to load eval_inner.py")
module = importlib.util.module_from_spec(spec)
sys.modules["eval_inner"] = module
for path in reversed(ADDED_PATHS):
    sys.path.insert(0, path)
try:
    spec.loader.exec_module(module)
    func = getattr(module, CALL_FUNC)
    value = func(*CALL_ARGS)
    RESULT_PATH.write_text(json.dumps({{"pass": _is_pass(value)}}), encoding="utf-8")
finally:
    for path in ADDED_PATHS:
        try:
            sys.path.remove(path)
        except ValueError:
            pass
"""
    runner_path.write_text(runner_code, encoding="utf-8")
    try:
        proc = subprocess.run(
            [BLENDER_PATH, "--background", "--factory-startup", "--python", str(runner_path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=600,
        )
    except Exception:
        return False
    if result_path.exists():
        try:
            payload = json.loads(result_path.read_text(encoding="utf-8"))
            return bool(payload.get("pass"))
        except Exception:
            return False
    return proc.returncode == 0


def _run() -> bool:
    import uuid

    runtime_base = Path(__file__).resolve().parent / "_runtime"
    runtime_base.mkdir(parents=True, exist_ok=True)
    root = runtime_base / ("engiworld_eval_" + uuid.uuid4().hex)
    root.mkdir(parents=True, exist_ok=False)
    try:
        _materialize_bundle(root)
        if _have_bpy():
            return _is_pass(_call_inner(root))
        return _run_via_blender(root)
    except Exception:
        return False
    finally:
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    print("True" if _run() else "False")
