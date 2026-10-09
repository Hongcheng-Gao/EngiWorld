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
CALL_ARGS = ['/home/user/Desktop/answer.blend', '/home/user/Desktop/render.png']
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
