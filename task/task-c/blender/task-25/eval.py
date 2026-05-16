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
CALL_ARGS = ['/home/user/Desktop/wood.png']
INIT_MAP = [('scene.blend', '/home/user/Desktop/scene.blend'), ('stub_gray.png', '/home/user/Desktop/stub_gray.png')]


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
