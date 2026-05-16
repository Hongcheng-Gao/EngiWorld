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
    print("true" if _run() else "false")
