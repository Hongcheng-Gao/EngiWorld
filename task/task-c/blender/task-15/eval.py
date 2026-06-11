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
