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
