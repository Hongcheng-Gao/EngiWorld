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
