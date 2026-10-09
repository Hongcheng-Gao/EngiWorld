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
