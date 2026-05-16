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
INIT_MAP = [('scene.blend', 'C:\\Users\\Administrator\\Desktop\\scene.blend'), ('textures\\panel_diffuse.png', 'C:\\Users\\Administrator\\Desktop\\textures\\panel_diffuse.png')]


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
