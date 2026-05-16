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
