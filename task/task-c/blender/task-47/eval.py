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
