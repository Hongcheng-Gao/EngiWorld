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
