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
