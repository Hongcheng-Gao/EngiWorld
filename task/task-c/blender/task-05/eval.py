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
