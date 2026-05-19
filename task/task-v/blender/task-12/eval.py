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



def _has_generated_python_file() -> bool:
    if not DESKTOP.exists():
        return False
    initial_python_names = {Path(rel).name for rel, _ in INIT_MAP if Path(rel).suffix.lower() == ".py"}
    allowed_names = {"eval.py"}
    allowed_names.update(initial_python_names)
    try:
        items = list(DESKTOP.iterdir())
    except Exception:
        return False
    for path in items:
        if path.name in allowed_names or path.name == "_runtime":
            continue
        try:
            if path.is_file() and path.suffix.lower() == ".py":
                return True
        except Exception:
            continue
    return False

def _run() -> bool:
    if _has_generated_python_file():
        return False

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
