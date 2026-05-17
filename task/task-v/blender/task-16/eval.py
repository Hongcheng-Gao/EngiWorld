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
