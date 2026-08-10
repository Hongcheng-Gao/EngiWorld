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
CALL_ARGS = ['/home/user/Desktop/normal_bake.png', '/home/user/Desktop/answer.blend']
INIT_MAP = [('hi_low.blend', '/home/user/Desktop/hi_low.blend'), ('stub_black.png', '/home/user/Desktop/stub_black.png')]


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
