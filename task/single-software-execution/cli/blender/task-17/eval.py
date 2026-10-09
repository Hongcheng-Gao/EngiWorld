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
INIT_MAP = [('sphere.blend', '/home/user/Desktop/sphere.blend'), ('textures/albedo.png', '/home/user/Desktop/textures/albedo.png'), ('textures/metallic.png', '/home/user/Desktop/textures/metallic.png'), ('textures/normal.png', '/home/user/Desktop/textures/normal.png'), ('textures/roughness.png', '/home/user/Desktop/textures/roughness.png')]


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
