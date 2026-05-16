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
INIT_MAP = [('env.exr', '/home/user/Desktop/env.exr'), ('scene.blend', '/home/user/Desktop/scene.blend')]


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
        score = result.get("score")
        if isinstance(score, (int, float)):
            return float(score) == 1.0
    for attr in ("all_passed", "passed"):
        if hasattr(result, attr):
            value = getattr(result, attr)
            if isinstance(value, bool):
                return value
    if hasattr(result, "score"):
        try:
            return float(getattr(result, "score")) == 1.0
        except Exception:
            pass
    return False


def _resolve_arg(spec: str):
    if spec == "__DESKTOP_DIR__":
        return str(DESKTOP)
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
        score = result.get("score")
        if isinstance(score, (int, float)):
            return float(score) == 1.0
    for attr in ("all_passed", "passed"):
        if hasattr(result, attr):
            value = getattr(result, attr)
            if isinstance(value, bool):
                return value
    if hasattr(result, "score"):
        try:
            return float(getattr(result, "score")) == 1.0
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
