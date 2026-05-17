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

BUNDLE = {'eval_inner.py': 'eNqVGWtz27jxO38FyvtgKich9iVpO2p0c5mc02YmSTPn5D7U1eAgCpQYkwRLUJZljf57dxcAX5LcVDO2SGDfu9gHFIbh9b3MNrLWFUvgr5bmjr35ePmSTdgX9VCzWrPrh7raLNWSfdArzYPgd1WlSaoMq9eyZn/g6h9sLQ2TzKTFKlPs0z9/vb5huV4iXMW2a20UqyulWKyLWqYF4qqgXuNSpf6zSSsgX+glEI1u6gqoIOO3m+pemTF7l2aZfRl7YdhHZdajMZPFMiAxgB5TVhUglcMuS4HLVrMI9Qrfvw9HbJkaEKBQMcIor1ZqMiBjAp2wf03WKl2ta3bJX7EfJ+xKTV6Axl+NXKlpwOCzyFSxBJ0mk4WM71aV3hRLeCl39VoXJAEvd7CAAAjKXpeyXj+v9XNZmK2qOK3+HIRhGCSVzpkQyabeVEoIlualrmrQqdC1rFNdmCDwa9WqlJVR/v2b0YV/1sY/mZ2xRJeylnEmjQGDur1maczAKdkyCIKbz9dv2YztSbFQL76BYUQhcxVOmf2E6NxwbAHUQ0mWE7EGkoUqagOAPw13H4W1IREBO7p9vyxqnTX0ycAOwMeBoDgAkNvAQ4V/VzpXdbX7BFs2Pr5oGx1OuCMojBmCOAfgAgnjyIHMx8EBrPJLY6mA/rO3axXf/abMJqttDKCJpszUFb2VaObllC20zmghNyu7e4LWTawr9VZWS0spRtJmyrLU1OAJcky0VIkEXiKRMRzL3Qw3RwHBwxaTy2VkVJaMSY6x4z9GtmP27Jm4246mjcoIyC0XLssSQi/qqBMdURg5Rr+UlS5VVe9atlkmLCBx7/CoFMRvQfpHHX4jPJyIFsXcIlKGiVladMU6y7CGQ5AJgwY7w/GKX7I0scRa8ZjKINtc8sugQ0os07g+Q2YfEhOIOKLU4TtmoaXp91oubVQ10WX1AdB9zG2I7Ft0bwMgCWamBfg+HFHpfE5Z63BotaooEw2VytICDv2M3YaTkD1jf/nrPHiK4LQnQS6rO8ANP7+5uQnRto3ryKjhuzfvP4Q9DGLnQysJGbvdI5HDnDVmeP3i5QFfUN9wFJzE9MKe2UbC7gSy/QVKd3HW8xco5MWBhadtm4QR+RYT39DfU36VHEbfL6MLoPDfRci/6bSICB4iOkD/QJ7cFHUnW4r7VOKpVibKlXMZ1IGvBaT6SZLCaYESgvtwxr/BVxHvGKAws5ZYH9VyBcJY/3+BwkaUoDIodCnWPwPWZg07MFCCy7iPtRnrEIMaR2hEBOqv3qzWPfpsoeqtUkQw52B01JDKNSs2+QIqH5BoVeJeCfp2pWaB5dfKucjBzvTOC7WNrOkgA7dht8g5liyBMGiW3gaKylVhsD5mWt9tSlFLqKBRD+we8sb/Aius4UEaqL+Rp93uQzQ1IDN22T8Wzs+XzSLUYrTwjBJ3VMlipSKH7jOoP6Xo10iO+gS36xTaJEvlVs7Zn2ZMTo/itd2f+edmaX4ELVsoOT8lvuwLtsGwi+SYLQbCVbBWLagckehj+7AY9aDAYJVEwavFWckrEr1aBL0URPEKHqB46+MmlLkSDvzUAwEnCKw4HKw7a9++agiSIoj1wdWY3JuAF46Fsgon5vZyDiqZ23TecVWldY3MjaojUjcdDYm3Dh4YFlkSvt0BdMhJwxBXGI0uMWArLKBjplZH6ETUu1JFuDpm6RKTphMfJSjoeMMep8Zo2gtZaCeFxcCwtU8nY/dLtVFB5/2dhFzp5ak2hcDWNaLmVGCmcAL4E13urKliaF3ASk0bEzkToiwaW1GOyDw1CQT4MTlPgmMTEyKMUA9whKCNsxKBY8JCM9slM+jr9y2NbvFwWiCt4CmiqDbStPRmQ3In0lG547o0fJvDlypEDtMK6YL/EG3WUYqw1EOsyhoGE/yCCGMwCamz6iLRnra4ADkZ9qCH3Kv/Q0lPyupIhKDVcEpRSPgPOAxa/dteiz93wpdUoEwX7FSj34I/Dqked/4WGBr9Y+DeGDB3EekGwC7cYBqYW61+gJ6PxlBmVWHW0YyGz4/XN/+w9Qg2seyAK7H/5hbW8JWyHe/IhyzCQW38BDoyOGnwyvEkYlYLkVp4yo0ZsBfOkoPgDU50Gxd7ZHm4YHlqcDxGRnhUiP73+PokPx/XDXVQw1F0hvrJGQoHc/UAo0S2Y6hnfza39oI344sZGsHvuoRGLhAO6DanrJRjVqIlsGNuzQYZKCTyzrGwLfSdK7ktkRECXtF0gBvt0kBxL4UoK2UgCEFtS3Fg5ySkFq7Rycz2Dd3DeKCw2+xIc9QphpGPaJASuh0l4/XIG3ZVIBbo1FKAemLzX2Ml6kMxqnygOaxOrNkVSukCbxFKv3kq5Fqoji3OhRzmzw5Z6IzTFSQGvFDBLs4b4onYo5ua2bGIwXdIRYE59E8LObvY21Jmo5ZsZj3SVrjRoY3iFxwoDu6N2Il7I4YB6LpRLGm2EgqzhuoVJZssOx77cJVXqsygqEe9qwFQI/QiUA9gCyw2Ao5nSwyP1+y7KnqDcqd2OGMhdMh+7IvqYHmmtzDatTg/QCe+rdJaeTfGstBFGkPYEyLle8M2OAW5aYCu8gwEMu92DG2z8NSlSr+F6AhsCA6St4gtZAOosvPU28uYs4ShomWW5veR7F7fnCXqrvhotgiPzxVAjtGBJ/M2HYL9hQ88mjcpl9KM6ZI5jJl7K2AnZl9y5i5VVe/EUcYDUphbaKOiiRZrAg1Ige8/kCeIzu9TtRWZ3EGa3pRQyfw8s1y56uYBm4tPsVSlWVWyXAssdq5BuRe2IGJqb0ERYLlqQOjKdOaAYSi2A5nvJsS9S+MOkmautJmgoDUe7Jc626104fbbpNHyRwetnEfDgQuQ38/skiyGtOH5KKm0t700/832gATpnnp0fEkal9Bsd09zHVVfFLY34/WVFnGmZPfwdfOj8/Erzt42gzbN+TSpI/PnONe0Ezx3BsJeCjPFE5cCznZDkzWwDjeXdbzu3XyyLotZ29Qd2ay9/W4FwK7Y4h5YW/n2DZHDqA3tP/P2ipzuj6YsyuUDtHkT6G8K8Thi27ReYwbSGdVOR89a4ZEaiHuIW/5ImfWeprtBSNnm4VEAwTF+yQfAgpfo0cAsCq/44GAg+u0gbuEmFm1gwKbnhKmlAnGGlpMLEzWkJrbJHbHXM9vBHhnxcdJw3Xu0KX+VHDUSSTiw5+MBf1TYE9nD347BH+2kObvdkxpEdIxMQDd6mTe+eCJke+FKAx4eFaE3dbmpTWcoGzfumWHnMWalNjWESJKuaMHVTEfv5JTI/dVqM9uqPK0j5O2wSygYdoG7C0s3QNuN8Pr3Nx/Eb9c3Xz98mWI5xF82+HIDgWeRGgYjzwJHsshRl9UKM5PZGY6P/riHk0mIoYVr7TF3wPh1i//sNUOEwCPgfDV1Qw5k+NNIHqK0C/SLDH9TrTY5hMBnfKsiaGDiKqVJcBY2dQB/UuOu5SoxKoV0aMieDApdh28vZthFjbyCeGhKTswQy0Qoi9211m49g9t2diZrgSUETXtCUAEVNM4K4SqmNWTwX5vvdNI='}
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
