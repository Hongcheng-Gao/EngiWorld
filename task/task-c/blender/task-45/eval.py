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
