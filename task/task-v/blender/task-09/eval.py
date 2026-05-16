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

BUNDLE = {'eval_inner.py': 'eNqVGmtz2zbyO38Fyn4w2ZMRy4rdG12VqdMqV0/SNhM7N9fxeWCKAiXWFMmSlGOdRv/9dhcvkpI8Oc9YIoHF7mLfC8j3/elTlK2jpqhYAv9NVD+y6S9nQ3bKbso0l+z6PXsr8zn3vLcZfMvqtNw0yyJnEhZy9nsp85o1S8nq9WyVNo2cMz5DSBbB/5Os0iSV9dhjbMjZVbWKmnUl2QMhf2DyOa2bmn1JmyU8R3GTbdglmxW5rFkerQDZW3g+G3JO35eABv6iqoryBUymOYtYneaLTLIyqmTesHgZwWiglrGqKJqBwnHJmrQMOWA452y6KpsNe7h+L/5ZRJnhAydHnH0sakk8sAe18oHFQBK2AXtCgcRFXjcV0GkU50RTxMUaBiYTZriE/TdRtZA0qEkhidfcUuZRnoJI0iIX86iJOEgAnh/YMqrZiCXxunoCqiDth6yICe5BIQ9QBhuRgkae2dmr4avzUPEyYo9yk1Qgu5rJKF6yqGH6dTscsOHFgI3OdsjGBWfvNShDIwAIYAVWoDblcyljVOYMVHlaRrjLoqjmaR41UikMxDyUpyNEdQmqzTKgbbi0rC+jJ0QG0iqLTE2BME4+XP82vfp0gmu/h7WWRcshMXH9/lQq8wRGvhRVhgJNM1YkRqXEsKyVTDp8L0C6hs0zfnbBAlBcXWRgkaySdTpfw3xTZBJMKZZgF97nOlrIMaGaKVNnp6ezKH5cVKDZOby0Lb/cwAACkK3/gBJ61RSvorz+IivlAW883/e9pCpWTIhkjYYvBEtXZVE1YB150ZBAas8zY9UCrLiW5v3PusjNM+x0aZ6L2jzVm1oRQOuJs6iuQYh6zg4NGLhgNvc8b/rvj9Ofbqc/i7e//za9YRMW+MpR/AFTT+f2aWSfXtunC/t06Yee9y17R9Zz+sbJXRu2VpexB+5Iv5/+8e7T1a9EfkvSHo7BnkFHA8boc8TPwoGauRizYMgvzMw5v9AzozOYOaWp1szOkSEa4mZ6C2Rq2QT79Dk4Sh2EsI9/XX34PBW3v38AWDRpsqZvrSMp7zDOYUyGe7DV2+uPeh3ZGC17yc50kAUbLos6VZLxvB+tqjz6ZD8tZfz4SdbrrFEGibFwzCDo0FuJep6PIUYVGQ2s6oWaPYDrJi4q+VNUzRWmGFHXY5ZBwAO2yTKCuUwioCUSiD9FtZngJMgF4WGKRfN5UMssGRAfA01/gGQH7LvvxOOXUCHHPwTkigqPSkgP86C1nWAPQ6gJ/VhWRSmrZuPIZplQgES9RaOS4Ew57T9o0Qsp5sKyIOZqIck7xjzRBjtGsAGPzESNAjtCccjPWJooZI49JjPIGGABXguVmKdxcwTN1ici/lhhatEF/1I4zZyjMrBYzJ+v9gOg25grE9m65UYGgBLETAPwvdvD0vo7JK3dzu2qorDY31SWYrqesDv/1Gffse//fu+9hHDc4WAVVY+w1v94dXPjo2yt6kio/rur6w9+ZwWRM6aV+IzdbRHJ7p5ZMfwwutzhC+4XAtXBlYbZI9OIWHsg254gdydHNX+CTJ7smH9YtokfkG4x4PX1PebDZBd+PY/agPz/5D7/s0jzgODBoj3Uj3iSMdhd3QTRgM20ivQSTCC8/qsCm1yvgiC6S++hyJvBVwg+zM5JVynqioqrYBSGFm21zgVmvYDymsBkp5HrXDMrN8pKoFCawz5t0Am0s4HoIN9B5uK4mKd1kmZyH51BwTHk+AgjVGkGieddBLKGXObnhS0xG7Z1ONqq1ptGXN5LSG+rNeFU+CZ9dLS2qTaOO9gpL8qaf1nBl8zFCko/2gt+4LJJa1O0Sj7HsmzYlL6wAILaTh7dLiLt7BYHWAIpAyP+Vv4fmzSo1B4JEQQGvalvO/W4qvWpgDTld7fw5sqU0gXICEVA1Wox+xOSfs2hxA18QqGZA20jaFqz37CMBsOCV95sSsm+AV+/+vTr1e3nT1P/kBRqxCPSWkSaOSsM74BnEVX00FVaYyNw0qdNDpqcIO3J1nCxO/k6MR7iRUtTSQyo2M1owaL0RE7VLITEGQUk8q0Z+RZwQLIjId/36aXPgiaADlhR4HCF1Fj0RJD42x7UjsgHdQgiccPWkrWQkLGceMqRp15ViK5Kzprmrc30WXUzggoj4BjXaAp7jOpxYEs/7SjY65cutFKZD1GWlVBCQVcHy7AkCbqchjtnbgb/QaVqg/8lhSKsipcbVQSN2X6TeG7sXfVOqqeEMN8U2F1oPIVxFdV9QRVKE0uDXhSY0dBOeuOQjlD0SpQUblVFhZKW+XoFcI3sb7IVepDwpGdCd4jAJVxThwvdDk962r1LIegP71FkKXvDzpSw0VMsCqgBoWZ1CJAMV2/KmGFta+wABgDoIgGn7zHWLQJ6oiN3PwIAMjTZ0dsPB1tkcDfWiptsO2zsWGDblG2PH5uDexbuCFOTD1be5rVn5v4/mM7KHX5DFEhn5IC9++rgQpskdFScc/xy3ZYyvnNuWyyJhxjK9qjbPRaZNbxzFoLWAfJQCE4fBYIIIuBykUFknO2rQmgfF76oTAABzZ/++vH2D38vWhhCKmrbJbvuFlxCUWhedP4R753cFFrYOrWVM9GkpXYvaM6kci8lQasETV0DvyzCIqdYDuucBHVwKe0J08uiVPQeBbKNkSN2BbVigbsN1ap4tqK9fu/fey8yhblDIw/ZG2h9D6cXA7LrChCSjJOhEw0lDrVi/NKeYDsa7O7sAJ+tIzWBvCJBUEXUNBUwNNDuogBg+iw8kiBbYJNt+shb7zYrdgirEzvM+WhiSPmR61M8UDeO7dFQ04RePdow6dbaILnXJUB30D88CZ27v3bufvCo0Bz69Q/elFFHWNIu9s8ZVV6KoK5BAPiAraHiqGKiHnpu8LdmesIityYkBImhkTAe8+bDZ53Y++2ZnSVvJamZdWLsWpyafsHgLDGLmoZBbMIcVULxv0ORt09WIQCraZuyE/I+zZ1eOm5nviSmEEwNADmiUY1PkoXpNgE8qz4b4LnnedjNiS3W7rqL7vHcJu7bbrOspBSGmFnaj63o0C3M5DWjPY3tHeNGWA3O0xhPkWto+OS8jcWcpLWUskcHwvToxQB9wdkUay61Qp+Au7NsbPW659dMHxr3yi0axCRbu1pLHW/3AGmwB0hF2fyYWkD3k45eAPS+Xzc9JsqUOmcgjyWiBDWaDYmywJjdVXmCQRECHZ03B48Y3flzGHZgHJW7hAwhK6JGw27CPjNaeOoI1C21R5/7FZte8U2rcLRHqT1uW9Lfr9icGtyJSgRd990WhLa7H1s76tANjx6iHIyXBsc+q2HnUAXDRo95dOWBq0qfZNxphdwpcdrIFchqvMeWW8smHURds+hpBIE7OtwDRF3M6sDCn7aQQ55m9rR6fFBSbVvfV0sHqqMe77jAW3pjyWSbQIG9KFx1/fSS0hIfuJ+4cvtpt1doW5/QFmX6SWtgR8tsZ2RUY7vXow1l9Gwupcyl2Asm1M0xlp3xV5S9dk9aHWZPVjtH9+Q0Q3tyr4eaBtxS5+7OugamH1dG2Au6l+7lOtdyTM+KGdUIaNMmOg50EmxnAO0lB8xApcQuKazZFa29GlUjFHiuGVWis06fMTjGjhtGx2YhHPejdpeh3TH7beUDR7W3S9hgS1ROL07YE6Y3a/XxPXUj+nKTzgQbdeJg7EapoI4ltfzY10Gp3AAdTmOuHKnoPsW6F7UlXxfHCBFXVorpgZ7CzkGnofmUyi8iizay4utyjocUDm4uy3oBu1/2+LQ3t8JCCGymWp1OuqBTZd10uQUIZhc5+HJ2qUCFuoG1TdqdadBcMMU7NqHuIFtLwEeq9FmP/4gIOQJ2VzXrMkOhBw4HB5tvvW06b/9tyUJdqrljeIewq6Nwv2XspidqRdJShUSxpa9dr5gjaj/QTwv0PeTA63cmhstJsHW8QMc15qNkN2DtwaEZ9HtY2kDnCijcAzK7A0LtjbZIdYaPE+uAWXK418kWP8f8dbLbWxY0RTbZOknsbA/VKTXpOgNNQRTrplw3desKwmlogh3GALv0Bqw5SRc00L1OOXgnws21n705kau0CZC2Xl1WWOCR0vVlmq7C1IQ/hewuPk1vPn+4Hfvsb/QTAD5fr8paLbIE7OUMXkAYt4ZeE+uLegNZHR5N9vJPT33qWmDM+b8Gxq87/ODUXAQIHALl4Vh5U7d2ai8yEKUaoJ8u8KtqsV7JvPmIbxW4cR1XKd17TMxvjST9wojr7Fqi9YtIL0PyJFCI9ZX8a51WoA4s2UOzQQynJSdiuAoKJeBFzSppO83gtLopImmBJAQdWQtBjZmgyxsh9MGREqT3P8OnHI4='}
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
