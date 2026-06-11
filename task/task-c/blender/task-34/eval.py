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
CALL_ARGS = ['/home/user/Desktop/answer.blend', '/home/user/Desktop/character.glb', '/home/user/Desktop/verify.blend']
INIT_MAP = [('ch.blend', '/home/user/Desktop/ch.blend')]


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
