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

BUNDLE = {'eval_inner.py': 'eNqdWP1u20YS/59PMdgCRzInb+Rrcu0JVVBfzr0GSOwgdvqPaxAraiUz5le5yzqGIOAeok/YJ7mZ3SW5kig3LQFb0u58/nZmdoaMsfNfRd4KXTWwwj8t1D28/XH6An7/329w2dR3ooT/CC0WeZXew/u2WUseBP/OZbmUzUn9qO+qEiTK4HBZy1KBvpOg2kWRKZXhFl8QKQj8S+9keq9mAcAph1WWS5CfM6UVLvyDw+t2IaGQ6g6qxSeZ6mHza7epdJbncCcUvBM6eVN+VBKyElReaZgi3QvubVhu2l/Uj3yJHvBCaNlkIieZLzm8KdbHabNCrCUR/pPDRWXkWjCSZ9DLgUYWIiuR6htDRRJ7KithIPmWAyIRHVoTw3wOp0jxLw6tQlDTRuLe0kqAtGpLDZH8nObtMivXEH4w2MMHqdpch/Acwp8y+YArF9VShjFKwkf+0pKFp3hYHxXKmZnlhT03ODlZiPR+3aDsJf7wj7F+xAUiMOf2XS303XNdPRelQhX2NF8FjLFg1VQFJMmq1W0jkwTNratG40mXlRYaz14FQbfWrGvRKNn9/qSqsvteqe6belRWKOGT5kIpxM/t9UsTjByZL4Mg+ApcFIYKRKurXdwoEIWGBwnLCi4urx2OYo2nobSJUgKbB2cfry+TN+/O/nueXJy9O7+COWzYDsRsAsxDmG1R+fe9QYH5D68puC29hboUhZxhzDbmV03eLGewqKrcLBRqbXdHZF2lVSNfi2ZpJbm8gRyjFK0z/kdLuRKoK1mJFHP3cU6bcWDocQvEchkpma8mxo6J0z8htRN49iy5f4itcHqIkFstXNSYxcvIcyc6kBA7Rd/XTVXLRj8OavM8sYRGu6ejkRgmpfE/8vTFpjIgW5Ryy2jKUGoS2yM7plBjrOWJIsCOaDzlU8hWVthgHsgcE3/Kp4EnKllmqT4iZsOMEjazkjy9GB1WZrc3aJn0UrqHWX+QdJNyGyKbgb3DAEUizGYBP7cHUrxnDK3tdvCqMZG871SelZghc7hhJwyewTff3gZPCZztWFCI5h552fuzqytG2PZHZ0BlP5y9ect2OIy6LrRWDOBmQ0K2t9DD8N3XL7b0g/xlcTDK2Rl7ZJsEuwyETUjWhUdPPiQjwy2wcWxXLDJnS8Vg/7xn/HS1jb/cRhdA7OeS8U9VVkaGHiM6oPNJmrZMqPBGprQmVG/dQbnShzeGPc4UKwIa1FeHyGUF+oglFwspJ2aeKbpbD8V1IjjVBkY0ib34sL79gHcFBvKKlVV/Y2vYDDL8M3EOkazgKaHXTWtkWnnzfXH2QsLrsKoVfyjwQ5YJXZbGfPpHlHPPD8vyFV5OJ3Bpm4S/2evfhiltfPFjTae+Yj5c+7b1UHwtdcSo6XBuE11SUdQbjkwZxC+qUtrOBhe5fqwlXeUML5Ef2R4yVoCRPgDkpO5VCRaS4pCUGEkmwyzlLqEJ5FVHbhoubA8wfR+aCr8Ye8biG4N7M1jspLu0IJdCE92GkcC1fpsIGdYwTakE2KbNamZdMDpjh6grpAPOgNwvIyl1RIX0e6FX2AsZTP3lm+ntDuY/H3g1wmHqij2Qritku4Vs8I5C9XDLc7KXnNCOMQglh73kcACagNzVQ4aYaothJbRuogILPC1SZ0EOsdiU3YLKru/F7TGbVg55R2i2SMPGqNpC9CCw2fHMo3SexqNRiQ01pp1OsjLBjsj4N0XDHDiTXu1O+g0jQd1IJctU/qnkc+k3qPWTsHffpuFwevGe+Z7VfU55Ir2I2U+xYU6w5muTZeO8I0nn8XdpZxrXQxe6RMpwNDj01Haq1s1+HDlwc+Ad3PTkPeHmMOL4bo7zjrk58I+7ae1nu4XZzoxi8Veioo+MCqVQVJq0KWwq9ykyOtHtPXScho0rLRqtHjJ9Z2PJTWgsvt3DuaySyu4NxzcxJaq3xsxq032Yp7vzoR35WH8vd8yj1XuzK38L1oSDIXN2pJRvet6b2cvb7SbknIddafXsfgUvXYkP+8vXbGM0GJCzAeRsfBQ+RDg7RNibgZ9C2EWOBy/ZcQzencF6DF5i/gN4jfwe3p3p/GlsifEYttboMWxtMlxT26j+QhLsJEPZZcKRFwh7KNtetd9OMpXQHTPp5eAVu4fxih19N4F3imHbTvZRWjH5ucaGBnvq08O9qLv1Nl+Qv7dDy0FTuQsPE5Z/IiK9mDShgTz70/3tKFaezgEtQsTbiMdxO/rGBh3fl/AHEHqI7SejJ8WDym/E7TRBg0RStbputfImgAl0aubmmoC6UjqtsNNemwU3ITh5oyMJ78bjfnCRRaYj0u246yYr7QJ3Q2ccexvs/Kezt8mH86uPb69nDP5uXgLxZVvUyjL1CuJOBeVm5KSLZv0rQqMecdLCr12vyU5w3kKAaG1ouhwxfdzQP56hPZ8jIo5R8+nMhsFup+YzdRS1XTAvr/hZs24LvETf068mWkqVNllNb7rm3VtUad6dcneF1xRjiXBspN4AirHVyF/arMHjoMYz7hyks6+5UUZcKiJb7K5FezgZ2raDmkELkUgSCpkkMR1vYgapJHENrwUy+D+AF5I3'}
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
        if "all_passed" in result:
            return bool(result["all_passed"])
        score = result.get("score", result.get("total_score"))
        if isinstance(score, (int, float)):
            return float(score) == 1.0
    for attr in ("all_passed", "passed"):
        if hasattr(result, attr):
            value = getattr(result, attr)
            if isinstance(value, bool):
                return value
    for attr in ("score", "total_score"):
        if hasattr(result, attr):
            try:
                return float(getattr(result, attr)) == 1.0
            except Exception:
                pass
    return False


def _resolve_arg(spec: str):
    if spec == "__DESKTOP_DIR__":
        return str(DESKTOP)
    desktop_prefix = "/home/user/Desktop"
    if spec.startswith(desktop_prefix):
        rel = spec[len(desktop_prefix):].lstrip("/")
        return str(DESKTOP / rel) if rel else str(DESKTOP)
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
        if "all_passed" in result:
            return bool(result["all_passed"])
        score = result.get("score", result.get("total_score"))
        if isinstance(score, (int, float)):
            return float(score) == 1.0
    for attr in ("all_passed", "passed"):
        if hasattr(result, attr):
            value = getattr(result, attr)
            if isinstance(value, bool):
                return value
    for attr in ("score", "total_score"):
        if hasattr(result, attr):
            try:
                return float(getattr(result, attr)) == 1.0
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
