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
INIT_MAP = [('scene.blend', '/home/user/Desktop/scene.blend'), ('textures/good_texture.png', '/home/user/Desktop/textures/good_texture.png')]


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
