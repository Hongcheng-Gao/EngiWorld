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
