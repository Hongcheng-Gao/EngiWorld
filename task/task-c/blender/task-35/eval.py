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

BUNDLE = {'eval_inner.py': 'eNq1Wm1z2zYS/s5fgTIfRMYS7MTXa6pamcquc81MrvXESa9zcYYCSdBiTJE8gkys0+i/3+4CfBEpJU6v9Yz1AgK7i2dfsLuQbduXH0VSiTIrWAT/pVB37OXPJ6dswt5e/8TyQn6M5SemqiISgWTyPs+KklvWVVVIdrUul1nKHFWGSeyzLE3WLme/ZGzh5+sFK+R/qriQIWdXolBSMZGy+fXFy5dEOooTaTm8UqFw4UnIgqUM7hQrl6KEF8lUINOaowJJslwWyZoJZS3eqvBKS3atBVtMfKFkyFailEUsEgUivlXiVk4tBn85CXrKJGyW52s2mSBbdpaLcnlcZsfEikR5blnzRGXEFkVe4BIvq8q8KpWDMzxcNMYJMihlOPslS+WYwewyyNIovqUBd2EhnPIexElFwpaiSKUCgiDXG9gbADAnBFgMsLASJpqvKT4bKQOUY6swose2iwqC/XE2t8p1HgdA9jyRaSiLiQYJ9q/SOM9lyZIsAyiT+A4AIAQe0Yaf8BP65tAr/q0kSKiuZPE2jUs2Y0+aJ1U+vwfhZsz+t02DrqYUyoj9jqIw+6LypTe3mcM5d9mmWYpT/inVcjADXrc0a9vSug5Ascz2GtXZfUrmAbPh0z52+FdmdzJlRk9TY64cNJKClmATZ8ctg2Oic2xs+3opAELeW/p8hzrJSfOYvbNsvzAEXxoTSFqwOI2yaRwimgPbtQdrgyzJitMIVpFIYRxFlZIXOAoUnBP+bMxO+FN6cQeroyQDDzJri6y6XaLpwcITfjqYDNLvjG2t3U+gqH9JlqP/glOCPXyKyyVY7BI8NqoSlkXg5rfyHlzlTq7BAsuMnDcv4tWxIowsP6vSUBSxVD8wWJPoyAIk4/QW7R+gRzqKDAHdRrAcwsvEhJUyyxIMEFaFyoStiGKtgxXyEbA1UHMYl3GWgnvZtm1FRbZinhdVJZDxPBav0D2ARpqVguZZVj1W3NLm6u8fVJbWnzNVfyqa52qtNPlQlCJIBPp0Tb8ZGoMvyyS0LOvny9eXgHymOEYNHsYQDVbSqb8LX+G7A7KC83ueCz72CKLTBCKmUpNmX6ysUuEnwGryFX/Wxa+vfn3tvfn1VaNeNIKTbzEesB2rCkCfqUwA60QWIg2kdfn71eXFm8ufPE1kzvZYXm/OuZlDj5+ZOZb1Y4OLRa/sAgP9a6mqpNThGTGZMlUWOlgjqOGU+aB3GlipW/10Dy2IHoW8EEWoKekzZAqRT6HXkxoc8F4BvDxwNjjn1jN82AlmIgwdJZNoTHKMDf8xsh2zx4+9u0/utPEKnMg1Fy4g1Kah09mOM6DgGkY/6vOrXLdsk8TTE4l7h0chwW5T2r/T4adPSVjmBFwvJC8I8MzoTjvEsATjTzyFgB3gCMcDiyNNrBWPyQScH+zG6pDywjgoD5DZ2MTEnmpKHb5jCJ9Es37WchkPQpOt9wNTNwHXJrJpl9cYAEmAmQbgfTug0g2Me9Dadk6igg7T/qaSGMIn2NI7e2Kzx+y7Z++tzxGc7kiwEsUdBv2r+fW1jdg2qiNQ7Rfzl6924z+xq00rshl7t0Ei2/esgeHs9GSLX3C/tmvtXVkLe+AxEjYeyDYjlG50UPMjFHK0ZfZ+bCPbId3CNjd9fU/5k2jrPlxGY0D2TWrzD1mcOjQfg8ijr4p8XwqMj3QCVp9BS5mAq6idRHaszzWdV7r8TxYAzQ1ifho2WYnnJ1lw52CqN8Y01kNVGzOEM+21RgaPPEoW4bzEz4vdBOmsXvjcXjAiOGZgo5iRcm3nmHzSAwioAvNqk2z3CdVEUAEUd0Bh9WQdlEUZLBG8IIFEmfkFlgcOvU1CmUOSUMLnO5iBJYFUmJ3SU51CxGlDySRWIECc6lMcTmVJGUYCi8COCsjhkjWvsTCnRIm5NVhdMYKlN+qolh4+2iN2BPrjUgUil04DJ46O7JHeAC6VXElRBEvHkBsTutogwR9WmJ4geoMYh4M6sWYvQI2EIcTbFBHRWIgICNI4QaWlj4EpcuCoe8fe2KBrjr7gNjxjdsZODvPT2NaJ+gf4FMOu9LdPSywhPgABqAvIlPSZodc875INlkaSdx/aeIbxCcYhXm3saS8BRgpH3fpAJu307d7pk+70D+1qWKcnfDP73E7NdxJyxclcHXcK4lod9zFZjEcps0OW3TrN5T3aoDbw1/84B4uM8wSqI0rgBFt8Ic8uxgwyAB9quTp0dUyX3cYfIbFvXIZYc6b9VLWLW//rWi9AoL3wi/a1a6bttFFX2hv1eAb/Nw68OO8mJ5Pvubw8en/kwvdxf2zUIbLvORJyR+15rOOIKQEf7hhlsR48dKg2cVb8FuqS3HniumO2O/R0OHTqGueQ9wGYDftNJJW8LIqs2M+8ax5N+dM3jU481fVSWyhhQ0RqG1kcrKXOoufaLIw19IPtn6zsvgRG4bt6/UtUNtDYH1AF+Zny6KRwBHjFGAsNowwQTdSiIX7+QTlfQO2+ExowF4YSyrlnE7Z22dkMyVJWdj9ma1TNf+OcGLp/RQ5xgVkP9of+iuSgqFIPabc9J4NXAMUOmElT+Dgm4X8E6TucRQm2zKDAUbxGF4repgCNFRaaA5o1XY61kE21qCYC5xOhDj5pp5nOmsAhNg2BbgJqtIKErM9RfFNURJBaUrMeMbOXp5y9VG23cD6FWq6Amo6isEldqBWxoM7Wgg8NmB7jmdxt29kFCCDTIAvhpJ7ZVRlNnuEI2rCa2YXME2zJwLmpWLTcPdUo8YKicskLKRD3jidc0huW6rAQxvbhGisPSXgoThdYpKYlgGQc1h7ClAYJBo9gMKmEypO4pETZcd+dvEeVk6S6wjAhSHkG7Xa9PlIVwuTYhKLhe1BiQ6VXqkV2RzWgzpbDN8WgaoBqIZUSUsky02rUahoR/1FdKhirNfxaLB/B+boSMWVZpl2syjhJ2EoKHKSOlE4ZmF+VkNhTahmJOKkK2SEDZ0McwNGNzVc/TrGjhO3fgAJQdlsp6sb+AHmU+IiNL4mNPAY+2aGBccaHxHYio0g3ibALBFK0HTUso2qLPuVMd0NN9xQ7ZNhfVzIt9YqlgBiJU1BPVP23Z0Gd5NJazHBNZ3VkMta+5lpa3j0uAe21Qz0F2qO2p3tjCN9ACj1Q3WYUYSuPSsWOsLpKXMUKi6lRx4n/ZrZ8/uUt+w/d8vmXt+wPt+x/ecvnD9+yf3jL33JG3eU2Mexumjlk7bovCvsN1y6vqynQlM4SZp+rDE0P3G3Qo5XU2evSgCMUHYjOVKwA7LaDbeO52Jm7B8WGM00zONLngeuPdurGGy0eIqnlOISn9notUIOt3soOtOiPcO6YiR2c/65xPv8DOPsPxvm8h7Pf4Ox/Bc7+w3D2Ozj7D8L5/P/A2X8gzt9xNriwYNi/EQW1AyBAQuh/ysp4BcHUyVJ4nAPm9dYM7qlX5Zg2Y10KHo64Y/K2k+HSDYlJbPfcknTSW1KRzm61goC4l6FGNZ/nM/a0BzdUSnSYeOb6xjP3PAC6XjxAvL2yuRlKc2OzAPDFdGBDPA8ddCSL2+L5rI4Pu+136qHgCQMrel12DSCk0HQs7Kt6O86s4cjuMCTMeok3kRizfmN/zJprgn5E3WEDLFLQugciAmjIYgDZcGezDXHdh46+QGWbvjxbdnQ8YZtGqG0Hve9rr9+P3m0hoSTv3UC0+Pmfwc/v4efvx88f4Hf+YPx8jR8JqRH09yJ4vgdB/ysQPP8cgk9OOJvXbotRa9EvLRdtpwOSo7RagR8Huijmhgj+zUN9NQVuvB5TiZvBguaOFQINJE69ohpSdmnSpA4lyq7MbXkh8DKP0lpd6CGBjuG39fzA6PVU/8DUHf2KdK0fY7ltOHQjOchSU+sMt1yQqlffCxwKZ19VsHciWs+GWobmbAPTaeXHM0enTbtyuft9kzfTZhuz8e1Yu9TwkQ+PBkZHzX022N6ouSbZUIjvSdMcKDvlDBW6f/D3FdMuuX3FMq/vqNy6CyFXcekgZ7MYEoZUD3Bz82NOE/3Avvxt/sp7fXn99tWbqc2O6GqYh9UqV3pRw8Asa26D6Gn/NkgT1Rc67YXL7nWQuWl5X9/0bKedax69C6x+HLMBUdx+BMTVWnH82B3Dt3f4wsE05b1jTyY2dr+fTKk+xK8oKc0m1rQAnmoANAW6GOfz4hZiQFrSb3gKJ5QqKGIqdWf1j4ek/skQ1uncpEw5Wq8nzFrkb2pIcxmr1brvRgkvY2Y26rD+LYGqfFAdXiBoO+n8XIfKNMMSmKEB5pzkRt7KwW3tlJQ4yneLypxT7V3LuPdXQRgH6p8zGXbanlrTayhTrwnYeXTn4HnUIfc81JznmUa5VqP1P2+WI3g='}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['/home/user/Desktop/output/scene.usda']
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
