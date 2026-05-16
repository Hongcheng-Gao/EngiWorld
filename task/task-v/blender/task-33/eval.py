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
    print("True" if _run() else "False")
