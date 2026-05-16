from __future__ import annotations

import base64
import importlib.util
import json
import subprocess
import shutil
import zlib
from pathlib import Path


DESKTOP = Path(r'C:\Users\Administrator\Desktop')
BLENDER_PATH = r"C:\Program Files\Blender Foundation\Blender5.1\blender.exe"

BUNDLE = {'eval_inner.py': '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'}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['C:\\Users\\Administrator\\Desktop\\answer.blend']
INIT_MAP = [('scene.blend', 'C:\\Users\\Administrator\\Desktop\\scene.blend')]


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
