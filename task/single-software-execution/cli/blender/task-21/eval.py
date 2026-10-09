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
INIT_MAP = [('character.blend', '/home/user/Desktop/character.blend'), ('scene.blend', '/home/user/Desktop/scene.blend'), ('walk.bvh', '/home/user/Desktop/walk.bvh')]


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
