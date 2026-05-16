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
CALL_ARGS = ['/home/user/Desktop/answer.blend', '/home/user/Desktop/output/render.png']
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
