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

BUNDLE = {'eval_inner.py': 'eJyNGWtz2zbyu34Fjv1gqhZRK7GnVzW6aZI6k5tLLpk4l+mMT0NTFCgxoUgeQCqiNPrvt7sASIqiHKuNTAL7wr4XchzndhMkZVBkkkXwrwjUN/b2/dUN89jnlRTC+5ALGRRxlrL3QbiK0zhdsixiAXsdqAJe+GDwqUwVi1MVLwR7lYh0IeSFYh+rYpWlkwGDz1yvMs+bB+G3pczKdAEvOYEwASLwvIIFBEBQ9iIPitUvRfZLkKrvQnJa/cdg8DJRGRPbPFNCsQdE9LOyyMtCuQTiI97wgc4itoWQaZCwVSBToQCDDxzHGUQyWzPfj8qilML3WbzOM1mwIE2zgk6qBgO7Jpd5IJWw719VltpnVSlNahEUQZgEyMDSqpdGLIpFshgMBncfb1+zKduTPpxs/lWEhZ8Ga+FMaMWo0xlpgK2/CpJI79FnzK9G5vEntgV1s3tvPGKX45lGqLoIV/zXBqHSCLR2Cd8Gaeev47SFA0hXo3or2PpBBDrUAFf8t4YerbMoCIWXRZHGKFZg1+XKl8EiLhUgXfFnN4ZaHqfNumHU3gtFCgT9aofbLkoBENc3wxbIQuTFysqKm2avyBLw0DQUzd7Vs9HgADr/o7bDgL7Z65UIv30SqkwK7ZhogAlThaS3HI24mLB5liW0sFZLvdtD6y7MpHgdyIWmFCJpNWFJrAqwM5ndXYgoAF4+KAoirJri5nBA8LDFgsXCVSKJRiTHyPAfIduhpoofhOCaPA/yHLzcbZ3DPUU1HP7IZQbBW1QNvyTxNSCxbfGQAoIhpYO7LX5DiIoForkh14gUWSF6UxvsHMMCIirxFWrqDEdwaxZHmlgjHhOJEmjIQYuUv4jD4gyZvUNMwAWIUovvCLyHaNq9hsuopmI/jj4PgO5Drn1j36BbHQBJUDMtwN/DCZXWp09bh0NzKkl5sXuoJIZ8BU5073gO+5n9+vfZ4DGCkyMJ1oH8BrjOx5d3dw7qtjYdKdV58/Kf75wjDGJnXStyGLvfI5HDjNVqePH82QFf8LzOcNCLaYU9s42ETeix/QVKd3HW8hco5MWBOf26jRyXbIv5tGvvCR9Hh+HTZTQO5Pw3dfjXLE5dggePHqB9fFmmPpaZdnnR+japfp5XR69roVa0QLVhDfBlESd1ZfgiMBP0APD5ZlVAwbWAr768/Qyv2lWACc9yxb+v4Y9IITXHaRQnwsUvlGnaEk+nI0hMoJ46SbkmRtGauA7V6P6oCmkXg2TK6u0ms840MsDDJgqDyZBrdMWXQmchzRlsinCxYv/OUsHAX+GVF1Uu2N/ALd/f3r11Go9FOTnmQUdB9UuEH+o66Gvizoi9CcAjTkMVnOBij1wPF2wdK0V9iWRQw6E3QSM4JzZGXkYLPkLAWVS5dscUVBkGVfdodBgt+9TK3uj3UbmPBbYMp2xMKbVWSU22gxA5e41zoMMwTdZVwxGrj40EpntLCuOSaPzE3meLGAqQhNIF7RZbl1CS5oKJdV5UvCP+2sD6BOsTDGgd3MlFynYbSgGIenUq5SkgSGyeQVzQPTordja1eO+yUHeUvzBpWi5WpuEqSJeQANw4hX4OCmkWTt2rEfzHoQ9ASPM6HOozAABYEHknhiAtA6BZtsR9UYIjWxw/w/ToBnPlwhvfDtkLcnuqdGaxMosdr2uD7KBDRsk04NCyblGHt1PquFj1Le6OKDX2KSACFTjo2q9VhObR50ACmumJYUh9ezrhhF9HhxE9V63nHT2Dap0uLul6T/IbeBK79WxwrU3na8wL6Kg8Fd/doVnkmOLIi8lFMLLsFoJiRquP587XI8yGMt5OyZ/o0f+eyQQK7gbaCjUFivRgc1mGmTCNoyzBXHcvdNtPgbzmYrEUFMCYEgSPVQ07M64AQ4RP9DDl3W8Ie2Ow9brB3nAoChAbSHHWsU+YAJlFTZtO2w1mjJG2sDqWyHq41ZKkN8oMD8+iU1V3UbAjDSA5XGyTOyZEtdXE7JE8B6RU02d4UEo1ffXX4Le5HDRPshLgWa8w2rPa7Ev6It2IBEpaneeZk2ba2q38TZ4khPtIRt9Sv7ThYca3p4bURqsamOoczK6B2fXBEBBIbeK8FgjDGGYpdwsmvDT108xws24ysWEPAxbBe0+FB/pVi371BPpVi/4P4YH+rgWvp8NHyXfA64nxCKmb0hqjd9yT1HqSybZT6Ee1ak0GMoqjt9lp+qoMQnWEUJ1H2BmE3RGCfZvVWW6DLYNpzPgbyG2v3mNum6/r0vYhZ89gLoBpVgYJMxOxt4JGikPrJ4s4hGUZVAxKXrCFHolqM7a+FljXNgDxMxkvwfempmd07VgMX2MoPFqrq7gYsZ99TL+bFUc0bETcBn/Ug+7B1DWE8H4Of6zgUeSRQCicu53CgD3UwgEHkE3QsL/AaR/smrOgYDsA+q0RNxWBPBL2uldagjsnst57gsAIaELQ0sSOE9MNdp3dtGVd1sJS9T7vtbU5P8oM+qa2GZm+xWBzvFEJpQh04xlFShS/w9QvVeGhxvQKyhSkhlgJI4iEERvvvsD8mhBM7lJs4gxINihJhndezehrLlaQv7lF8XOUzG3NjNTDGgopu8f7FZh0YlqPcUli7+COwRxXw9kEBSIYzuky5Uhj0kcvaGyp6Z5Y035WveZEGk+ypf1AuVi1jTjpWtFmfS1OtxaQ3bWXoZ6whoFMj+jOeC4tGVeqER/xpcabWvAe3TrdNMmwcxlGnoX6Nq7V6h90rvDbgnYTIzqUnaeoyhvvp/bPHuAkb9bhvL8wxGngbhPTw/ardx9e/+v2z4vD76epEVl5SASDfjc92d9HF/smqib8eXSwXE6i0rDDx15eJrRIoYSrDX2GqdV9i2ef+Y6YOu1E/XzCcogLxFKcvcHQJeVAbGK+u/yLlAeJzq2m4LeY7q7BwisBYkLMe38ZUna8QqQ5NIrQP6GDFGwLPnU5Jt+4vsFnmBdumJuV9u4U5VzIOEnEwsw0eeVDRtj59Qx+fDmqexSd2P08KalztSF2+QzDy1JoZVwEHLGeGG0Rgn1LxxvXsXqlQ/XahqpBgFpZqhZn7xxnAuzLDm1CTZK4PM9ZbHOflFsfu9M01ZHX3BXPOphWbM/9Marmirww0ADJKpIdOVe7sOAuNJ9A7VjYIWv1QiSDTje1gs5SpF0g6XUPYbur3uIN3sqfD9EBFV727I7LuPY+cG5yQPTSKahdWzeK9BG7PgX0upYF2F67GhKjJ3kTADc1HDuL82m3rRaAJKX0ds0nCRaNSjHezarWuEi6NgtdzpBcJ/kUdKbDe3s+DWofoLaxToOk0nMZqWf69p7Ax3jGMaNTZ/oBp8z6jXWHRziS0o/5dSzWm2mPR7ejsU1fsIp1XLi4YHqZXMapXuDmctx4nd5wbr+8fOd/ur37z7vPEwdGIfxJji/Kda40kv2dYDi0d7hnfiUcYVCBk4rFFEUGB89UEWZpFC9pwcjjOM5b/fshw0pdARjIwRn96El9cZkkxKPUN1nw/8NDw+bhAX2qdXroCBlKyL7HxYp9EzCVPjzQ1fXDwwge9T04PqMvQsvo0S0/dIJFgPfE+BNmS5e9N9SNFowO8A7OdouBXG7w6rNSHB/ba/jnHr84+J/Yuo7nOThvjiczNDq+YitJ0GTte51jc41Lv5Xyl3JZrkFXH/FNuguhQhnnqJup/bVZ0G/M3Iz4OQaqHxg0ZEpHcUZwxv+VsQQLfZaluV4GMExQOSdmiKVclEfvandqdILb+sdjcgc4g0/X3b5PN68+3aT7vrmQ1loa/B+TzC2c'}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = [r'/home/user/Desktop/answer.blend']
INIT_MAP = [('scene.blend', r'/home/user/Desktop/scene.blend')]


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
