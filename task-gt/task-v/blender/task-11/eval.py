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

BUNDLE = {'eval_inner.py': 'eNrNGmtv2zjyu34FT4tD5MZWnPRxhVEHm7buA5ekRZLdO6BXaBmLsrXRa0U5ti/If7+ZISlRlp2ke182QBKL5LyH85Jd153c8mTBq7xkEfxWXN6wd2fDQzYYsA+lELJaJ4IlcSYGvKxYKbJQlL7j/CrKOIqFZNWcV/BHMLm4TuOqEiHzrxM4NnIYO/TZZBXLSjKehSwvRCZ9WD7y2ScumZyKTPga5UKKIKoJjsfsqlwIPPxcHQYqieCyYnkm2G0slkHC16Jky7ias53AL3z2JVM8WjBzxEdCSVEpDFIkYloFMk7m+UKAGGwfwOFHb0xLIA6L5vk6L4FrxpOkpvXSZxckCzF79PLVCn6BLGcTcSsEq3IgWom0YF/PP/ZJI6g3JT+oLU75TCiiwOBIfcKfAUsFz1iySOOMZ1PBvIv9j/tvewfP2fGYDf3XR8xLc1kla7acx8C6kihPleFkz0aV8HIGemLTPMtAEKA7zdMClJpVLM6Io5CXN4MiXomEpeAPDTRjXsPEG6B81GcvBhpTfBtX657SrbHV4XDICBGY3flFgnxKLHIQUN9gcM2nN7MyX4AyBoNiXc3zjAlwSb9YowvCATzK3hS8mh9U+QHP5BK8hVaPHdd1najMUxYE0aJalCIIQI1FDp7KsyyveBXnmXQcs1bOCl5KYZ5/l3lmPufSfJLr+iNaK4oToYiEvOLThEsJbq8P1Et9BrchCR3HOZucnAdvLz5//HR1Prm8DM4+nzNlJef08/kkODu5/Gfw7svZ1y/nk/MrvQ2KUrunv5ydBFefLiaXn76cvifAo6Ez+ffXyburyfvgX7ACXtUsfNILjvNzzYtDf9m7uZjeXAi5SCql9YynYsRkVdJTgYKEI3ad5wktpHKmdrfgupzmpXjHy1BhmiJqOQL3AiOPleheKCIOtIKITyGcrMe42XPoPGwxHoYeXJ6oT3z0Nf0+ku2zZ8+Cm2Wv8Xk86CsqPi8gboSeJY7XwdDThH4uSogyZbVuyCZJoA4SdYtGKcBjMpLfs+j16GYCmDf1FSBFxineDvvYLoIVuF0SSFTYDoqH/pDFkULWsMfglggw99CxUAVhPK12oLlziYg7Upgsun3mKpxmr6HSt28z/bhKHjh6N/WVi9w14EYHgBLUTAvw/76DxfrZpq37+0YqFfA2haJIBb70zR247Bn7x+vvzkMIRy0OUohYAOt+Pbm8dFG3telIqe6Hk8+nbguCyBnXilzGvt0hkvvvrFbDm+ev7/EB5XV7zlZIw+yObUSsbyC720Pu9nZafg+Z3Ltn7nbdRq5HtgUx7zbtPfIPo/ve03nUDuT+J3P93/M483SacBy0TwBwyTrAKBwoWwWQJqs4m0mPUra2GgTfD3kJmUClN5PwqIyALILwQGmg8zuGarrZdtIX2QwoG7bAgG9PJ+fvJxfBZPLrZGIDCKThV5zXLPG0SMhjDl91EZdC5skCo3+wQsRNAH3w7Lp19tODZ+HWw04FOU3H785hyBxpUJWQsiDrYH4dsw8cTN09Sam/1jICQj2TlylHmD0oF/YehZnmSV4GaR4KlGHv4uPbk6cChaKAegGAXiuIn9hlBTEQoj0VTYxEQHagpqDghe7CIXsf05MEWswrIPuq8qPnW3Sp6qrp0VODDkgaSns7YZI8x7u9dw41yu5TYlXkckHXA0PormMznqYc7YVhVnl7FGdhUJSgmXLdFJEBwlG1uOnzF+ryoItHcSmrh4vRMVaHfQZ3AvmvbwFektuEYlrDJeGwIhtEitukXRi3w56+x7cqf+snpLNVNl3veg2tB4QyxXGuFhuYPckaJdV6reXCCzkTUHhVpUUIskcXyO0TryosgawAG0ta6qQ6kqkObKKyqURQe7lmfRNnfV5jRkNA6eiZ9R42C8Pd9PSzOf5t+N2oNsl5GJSzax5E8LGSXpHNAqxSO0r1ln027+s6GE7zyobrkS9w7AmoV7gu1rU2dZEJS/pxBnLjASzP1F3G+8HDhjgdrMp1IxJSBzAA9mX8XwEi9JuHwybLZnBoCYliDr8v6tVihTkZrtR3WM4a1wQEurAH9gWfzgOwh1esFAPgd5DeLCY2mS5Fmt8KD9D0bD1rTa2MkrHvCa7LeDavwAAygFhBbhxgX9LSa6P1d9DOLKAJ2uiZqKhj1/BUrsme1Nv4qiw5a58FZ2laLH4rSuAZ2tdb3fCZjgYhr+YKEcIcQvyDTs6CfcO2FPV9NqSM7xuOVXEeKLTGCsqQmOOtkEaUwAXWFcTfkq89A9XDqD08OGSQlRR/Cn5ewvEtPNRBKMYYBAF5Jhpcltmw5wXfabkEolQnv12rnnjYeNGss2m52HVn86jZXMOmV8LaDH6ve+wAOv9hvas0sT9mazs8rkHDIONmMShvvsXfMcorpaFxxxrDQaNogK8/H2ub1JrWDomwfdUFm3uv+ueg7pqDF9gAa2fEk40rfq7AdaAxhqAKWSwcQF5PcAyAYZnCqmnG6ybabse1b/6GOH9D/+IYumbVfLB8Nm98gHlg9x7OHpBjSXhV8z6FthoieKRdQVi9v+n484gdDmx/Nu54G8sYubGdjfxS3VeDCVzTlAwpXI1BLOdqjsG8Vy9vgKuvCQcHe/vhUuVG7AkHXA7+WIgF3TNQhb4I6I2ywiFT7ZGKYCshknHp2HcK3RjQNa96ue0MoFdINgtRL/6EzPhNowl9Ll4pDVyvt3HWvkQgEDhrwSnCzqFeU5jaxOMQoydt+EVeeL3WLuHZtzHjD0Ig3N/ZsrW+1usHBxsbP4H3ZAJC5HVeSr9NPwJ0x3Z+q4N9rNENNsjbas7gEmHYzPKq1gesjbY2KNYBNt6CtFa2aUuyuNdl9g0EP2DpAYb3/0oMrx/V7vKvxOwbSO6PafevwDC2yHg5jk2cadNogg+eatVpasfE6nKRURvr0bjQrs6sykoNtLDZGTdjLk+PdzBH5Dgc9BHYjyW2Zl10BoWPQy6X2jdBc2+oR6nl60P/nuV6Mo7z0bsGhz1c0HIgLuchpKqriFyFb7yJrlsFYgGWF9Jfpj6O4aGAijOSBf8g2NgSiqDEagp9IZvQP2h4GZdM7BSXZvu2tLjAIg574YjdiR8Q0qBSMhIiERqhqF3SVTDGdrGqfFpzdB6iMSE7Gj3wdkEjCqhZUeO/nWd7mxzWbYzIOKgsDAjW3ZirEfaNtch96IUHuyOY2npGkuej7qsP1rzGaGNBlan0nSjpntrdPiplDbApqaIEmRzvCfZNHamt/hikpPM0YFP9LUJT5YWwHelfHLw8eDWqu1H18gWdEdqomVSGrF/ZBDQoUG9q1Gf1lkZ9tkYvDUQqZw2IetAw6gEvbaPeRhLXqRv0DfGtiWbXAHULjlCteJdsaX5/kFevO9oF7q1G3mK/oY2630lSKxFuCNSHnVdk7QzT6F3N8jbA1HYbpDHPVhC13XtYH12pIzMNgFa3yzTdNFtCOzJZcijs23DpV4GApxb53t0m124U+u0hxm2jAo2iuYMWk/oSQkxscd7f0MbmLdbsNdAtM/U3pN2E1py1oWt2+xuC1vf2BIfHZvhLL/nMvIeKB72m3oWqV6GqZn186qyzWloEYYy6My/n/PQmxM9eUYooXo3daTo8bCHSFkbQIkObmHxOw2+NEVKNBePDQQ22OdOldIn0FboHkm09NKYXHssSKqJAVtAE0lTwB9OsUcpiOhUibOVardTt2bbBsDFN0SbFH40J44XCtRW+nrxYza/qSBtmtqLYnfC7QpnKpn4tPjhmd1rVdXrYXpbpU1trsifJjjM4sEAYy5v/SwHb8dha2D6m66txW3e2aCT7MY95VGYITUDpUb95itgPoupIDvajgUmP/Q0iePNypm+9fPlTZnS2vDdbZGJVqNkKdRV3y/vV3fxPi/rnSHRU0EyW0OJPGnSuNkN0Rxtt3mjwdTxmW76R0CnSNqalkJlwZeS/iDpvJCPXW/KsQsx3W1CP/CP1MnJjUPSUyZnzdGu0eTJkjvW0s/sli47E7dmbNRMDsfTePd7HB6TfQaqRvmV16kkpxeSLqljAtW5arj4zDjSmGpoVuayAryie0YK+DBrf1sbWN98WqN/jijSuPKStoaEKzdSCSUm9nrXhTn49OQ0uJpe/nF6NXLZPX4/xw0VaSAVUE+gZEthFeho7qOwWW/K19PGjuefuYODiRA/XmhutD+O/b/jHhypZrDw83MMRz0hN4trFqQ1kThRqgb7W45+Us0UKJvyKT6UXCjktY4qRY/M9N0HfbvP1zSzQzwKuwZA8KRTuein+WMSQfqxMDcewoi98IoZQ0kNe1K7SdmMZ3FbtPmkLNBEE2PUEAc4t3YA68CBwR3qwj4p0/gefjtdZ'}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['C:\\Users\\Administrator\\Desktop\\answer.blend']
INIT_MAP = [('scene.blend', 'C:\\Users\\Administrator\\Desktop\\scene.blend')]


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
