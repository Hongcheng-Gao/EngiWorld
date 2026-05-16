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
