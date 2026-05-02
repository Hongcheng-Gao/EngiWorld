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
