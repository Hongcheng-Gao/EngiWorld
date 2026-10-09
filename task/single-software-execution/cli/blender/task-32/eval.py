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
