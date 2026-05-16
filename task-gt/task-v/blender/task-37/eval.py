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
