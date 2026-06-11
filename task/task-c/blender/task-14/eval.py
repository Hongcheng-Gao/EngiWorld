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
