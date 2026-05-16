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
