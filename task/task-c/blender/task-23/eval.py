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
