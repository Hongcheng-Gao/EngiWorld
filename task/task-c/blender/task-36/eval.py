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
CALL_ARGS = ['/home/user/Desktop/answer.blend']
INIT_MAP = [('scene.blend', '/home/user/Desktop/scene.blend'), ('textures/blue.png', '/home/user/Desktop/textures/blue.png'), ('textures/green.png', '/home/user/Desktop/textures/green.png'), ('textures/red.png', '/home/user/Desktop/textures/red.png')]


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
