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
