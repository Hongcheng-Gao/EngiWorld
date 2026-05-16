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
CALL_ARGS = ['/home/user/Desktop/answer.blend', '/home/user/Desktop/output/character.glb', '/home/user/Desktop/output/verify.blend']
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
