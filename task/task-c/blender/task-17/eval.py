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
