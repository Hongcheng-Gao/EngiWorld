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

BUNDLE = {'eval_inner.py': 'eNqtWHtvGzcS/38/xWDvD++mMutc3WsgVEWlVEUPSNPAdooDfAazXlHSxtrHkZRjQRBwH+I+4X2SmxlyH5JWblKcAUsrcuY3D86LG4bh9DFZrRNbapjjv03MA7z55eJb+O+//wMTXT6oAsY6T+xaqyH8tK5WWZpYBZOyUPA2yZURQfC70tk8UwbsMrHDAOAFfLjKFh8gM5Ag/9Wv45v3V1P4lNklXMI98hookHkG6ilJ7WqDPABbAhVXZWkHjC/G/nviv2+yaicY/mapoEq0KiykyyQrSBIxQlSUfiOG8x9gTB8T+kBex/rh+iErnGrw6/T6F6dVV828nJE5GqoyK2xWLMCWzqA9hGVi4FFpq55goct1ZWpjAN2VLpkP1XT2srnG8U+Ra+NZz5mVd0ErU64eyY0l6sZcZcEYOlugm9+bZKGG7Kr7lSpmqOH5+X2SPhBGMcMf1cYukUXhmYpqgwtEQKTwfZXY5de2/DopzCelBa/+EIRhGMx1mYOU8zWdsZSQ5VWpLXqkKG1is7IwQVCv6QU616j690dTFvVzaeonszEOdJbYJF0lxqBNfq9ZGgC6eDULgmD6j3fT1zfTn+Tkt7dT+XaMhwIj2IZNNIQDcD/GzdOkecJzDXeI8mODHPAnvF6q9OFKmfXKOp+Rj4dgrOZfFak1G6KbyxUv5GbhdnuwrtNSq9eJnjmklKDNEFaZsagqGxLN1DxBWXKOMVDqzYg244DpcQuS2SwyajUfsB4DL39AYgfw4oV8+BQ7cPojQuGkiKSq8KiijjnREULsBf1Y6bLCuNq0Ylcr6QhZekeGVnjeBdsfdeTFePAzYotS4Ri5MKSASdYlOyXQYtCspCGHnZD4UlxANndgrXqgVkbBhbgIOlBylqX2BMw2ZCHh0CF15GJoOMx6r5UyaFDqv9DZg6TbVLgQ2bbstQ8QEt3MC/i9O0Lp/PV5a7drrdKcuYdGrTKqiSO4Dc9DLBHfvboLngMc7mmQJ/oBecN34+vrkHzbHB07Nfx5/Pc34R4Hi6tDax4C3G4JZHcHjRu+/+bVjn6QvWEc9HLWyp7YJmCfgbA9I+3OTp78GSl5toOw37fzMOKzpcpweN5D8XK+iz9fRx9A4T+LUHzEEh8xPUZ0QOcj9bqQVEEjrpGSCqc/KF/D7quNO84UKwIq1FSHyGcF2oi1EyuiIGaRmXm2UsdwNYSg2hASjVRPWDUMFrefE3QK1sgQ+5kr1pBY2LYY3TPxBhFW8BzojV4zpsMbHcIxr9WbVju0VJSVEZ9y/FKFzLHVsi30QWyjjlHMpZ5SVVmY8hf2DsAmqU6aS6B71tICzBPcw9K8VV9gZA3lbGQgzGBv1F/gr6IZY/xs4rwieB/7K7qDrKXKL8r7jyrFvYWyUYjEXgukkiUlGpHj/EBn/Ja6NFVMatF2U2GAYiLWo0R4oCkhZEYmXhNU12EelKU5CYUK5wGcY9APB/KOkmQekuTRFvVNrNUR0g/gjNbOBswR1470kemkDnt96+aL0pUjamIE5/zCq3FDIHmm4TjiksGV6p4qFRPuat9/IzAe3GTkhz/R4xdGTHGQsfISHYNxFTl55NHLIw/xeMTkpEBLvYNIPVV4fFhYLuM2AC6Fm1mdzjyhQUNolK2Ht0PVWkMlM4UHmnQdMYKeWaZXc/aawWKCfblF2FP+6Ixr+h4Z8a5j6bcC3nVG4yEPxhGHQe9IjDZsWH57kjgWHR2mG3wQ0OVA1KjXGdSY3INRUvjn2w7JnfBzOwY06dTAEH095nGoNlB7jjiGHe9h1kny2UwudClrWyV7lJp8mVKTP6PU5JRS4z6NaPL9Ao2I/E/o1GU70GritIr9PE0UUitukRhJDa4LqKiGpY99QCxKkXvot+UP/7pad+HjQxieNDgT9qarWnhPZjHd7qAmeFtdNmgMGJnIe2nRU4MmRY7S3jHhrWG756pdm7h/E0A3S8BKsISv2n7V3Efv+ZqHt8Mrug/yRYHoT3UuAvN1n+hc3jLHYfOixbZ70a34sHMxALYu0g2t9HhHRrL+beM6FPaHnYsYnm9dXvIzvQu7q0SX8TSd8/nmPD2TjbUrDcHlPQ37rgvhKx01lxqUu9HLoD8Ga6Lbizt/EicT7TmmNs3a2YO0aXLrtoGKnA0DqB2YewwcgQgl9E6MT/mBke76DrseUmRNKzn8JN7KsF0jcOukozBo3YyFoFW9E+vf+Vjff4Hi2jK98ei05jwpbJZSj3Yx/7hoB4/HRTt5PC4a8xyqdKi7Puv2KPo7eyvn8/r6viltf69x/j/d/ZU4+f4IryGYeVVZzNwrpMLNuPQiinq4816eGUMrWAmcwMKVQPJdYzHlGsetb//egANHFqX0aG5402qusLKlyhy6kjLIk3ICXRw7z7uNX8bhnad5hUbIWEk8dxNBe1nP9za6sslybau1NZ271qAJpRFlwgCq0ti0xGvMghf8Xczj9V7+RP0iorkiqjyzEcn23JXOCrcg/PU+jjsb4fT38Rt5Nb1+/+ZmGGJpp/dmYrbOK+OYGgFxLYJuWpFHT/Tikc5rg3dafKyrYXh+zgMXrbXl0BPT1y19iAz1eYqIOEbJL4cu2akT9jPVFJVb4Pd9YqwX6xxr+jv6paOZMqnO+II3qt8gK35vLHy9qihEsIY4NhLPDqUbj/rXOtN4HHRTi2sDKWEqwcKIy0Ski9t13m5PhrbdlZi9hZ6QHJ9Scs2UfEuVMnTmOUcG/wO9E+QW'}
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
