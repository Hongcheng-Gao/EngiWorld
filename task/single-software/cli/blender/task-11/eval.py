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
