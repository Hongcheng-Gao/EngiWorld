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
