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
