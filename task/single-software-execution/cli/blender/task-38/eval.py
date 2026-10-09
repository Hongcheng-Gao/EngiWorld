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
INIT_MAP = [('materials.blend', '/home/user/Desktop/materials.blend'), ('scene.blend', '/home/user/Desktop/scene.blend')]


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
