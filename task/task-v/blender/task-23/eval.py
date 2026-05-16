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
