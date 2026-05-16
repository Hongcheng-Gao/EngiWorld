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
INIT_MAP = [('character.blend', '/home/user/Desktop/character.blend')]


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
