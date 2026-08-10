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
CALL_ARGS = ['/home/user/Desktop/output/scene.usda']
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
