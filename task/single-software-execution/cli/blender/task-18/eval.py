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
