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
CALL_ARGS = ['/home/user/Desktop/city.usda']
INIT_MAP = [('scene.blend', '/home/user/Desktop/scene.blend')]


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
