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

BUNDLE = {'eval_inner.py': 'eNqdGe1u2zjyv56CpwOucldW4mzaHrxxsE0umxbo9oKk20WRC7i0RNtqZEkl5cSuYOAe4p7wnuRmhtSXP9LeBmgtkvM9w5kh6bruxYNIFqLIFJvAv0Loe3b55nDA/vvv/7ArlYUyWiiRsN+zLGK/ikKqWCSB43yEj0ksNStmooD/JBuLexmxR4S7en85dBgbBOxiGetCw/dRwN5q9mJwtIR/MP4xYG+EZoKNVfaYstlCMm8uRcqu2Smjj8vq4+wnZlfilN0eBkc+Owxe3fWAyrGhMhZpFKdT5p2O2DH7KlXWD1WmNcxplk2YlyzmgvUZsOJIqsdEkgG8YKFMC1APSMEfLCPRF4Yo4TwI0LeIs5R5uohAosPg8AUCvbScs2LGIqHuGYjAkng6K5iSU0DQoA/IS1ROAG3wwmdzsTQTSOe45zi/aTGVQ+I+TmQaScX6/bEI76cqWwDBfj9fFTPgLsFLQb6CCZwD0U9yUcwOiuwADR7AzCliIo1mSaT6UaqAZk8d13WdicrmjPPJolgoyTmL53mmCpA9zQpSUztONaemuVBaVuPPOkur7zkwqL4zXX3plTYMIlGIMBFaQ3jYtXrKZxA1SeQ4zs3VxTkbsZK0d+M5WILr+Kt0h6z58yBafAybnm/gKFz4NUeXtyA9CItDiovDChKszzEUeB0KBH/cWkZfcPBrixD6t4IQS46uJbAGhFzZooE+74KAbw99Zw06/lzr7dD/7Hwmw/trqRdJYdyeirkcMl0oGuVotGgIYZWZmJzrqVndQesmzJQ8FyoylEIkrYcQhLoAu5KZvUhOBPDiExHCFl+NcBHiDuFhiYko8rRMJj7J4Vv+PrL12fPn/P6xZ4jjHwIGhksg8hyCymup421R6FlGP+cqy6UqVg3bJOEGkLi3eCgJkZmS/l6LX4+2F6B5YWAQKVuFmBHaYPsYFhDeCddosD0cB8EhiyeGWCMek4mWGBNOixSP4rDYQ6Z0iQmEAlFq8fWZa2hWaw0X32Ebf67RB0DLMDAhUjbolQ2AJJiZJuB3vUWl9bfLWut1o5Wi5LOpVBKnsIVH7Nbtu+w5e/X3O+cpgsOOBHPMiiPmXr2+uXHRtrXryKjuL6/fvnM7GMSuCq2Jy9htiUTWd6w2w8mPx2scoL5uz9mJWQm7ZxkJ2x3Iymco3bO9nn+GQj5bM3e3bSeuR77FNLbp72EwmKx73y+jDSD3X6kbfM7i1CN4iGgH/cOTTEQ8j5cglgfZnmOOt56CxP4OVqGaQd1lDzHUVKgUuGEsTe8xjoqZz2YScxVk4EQUXE3Hgk+AbKF7AdYGJGWzNeDb4RRUg1GAuSegHK0DFKWWwTd5h0ss9JBkR78IMJxRq1CrJiQegT8QA5IBZvnbwzu/GQyawDI6AiSmKg8hzIwhOYlT8FGL7KZwSs6zB4l4BsGaALn7lnZtUsjZnvIZpLqxNaWFhmIyOHoJDlLsB6wpgxdHMJjS4PDVEQ7GFRXsKbplxjNsfMsUAVaNq86hsEOtjKfp9/UoMGZ/EI0/ajchKO1LYzbci0vci0qkU+m1c3YMUB5hg8yPoMCyBx/HTVAipSoojUWM9LfxXWWv2xjwBt3h0V3P2Jc6sxHTizkpAJn6gEG/YQemMEGPJRVsKRA4AQ0JBWVOmG2QtNHjawggh0ZDoQuORqpnEOEBESpyLSWhooy199CDRmsg+y+7eSjMUgjMhWzqGNAcINID9mFmo/cHbWoN978Ae9pKGj/r+S4HkPsHINkYtSW8bsfV19An7avYMVuH+jMvhELumy6wvblbO9Kx0kGvBl1XgEBBrCdxIr0tNFIcKAZY4V2zTFtUuz6jLQppwE0zw5BBC182NNqZ1Ui+vZ1x32W5Dh7n8CNTPhdxSqLgf0hk1JKJsOQylHkBJwL8wY4aQhjm9suLdDvi4gSbCGAALVIJuHsE3Ufog1pgGW63xQzXoKjazmGcAWo75WXjzzIsdDCVheee4aplCS1wG25uT0YWEk9LcFiysFBQIBhoA3iGQ6zJi++zVFJ00WxQrHIoJVAyf724eePSArLZAN4qRSJdeTrJCBDhcaeYcWoJd0W0O7dlJQTiQJpXMDxXUkv1AJbxa/E32pSJsceoBI1FUSijms+eoRrPfJK3t2bWFKNyQ5V1ZfM0i2Sd7wEowAleKCnpCzIKxDwiW3sECy25QapmagyzmW1aNLMgDFIvcQQ+53GEjQQZCafQSETMtE95feLlGXYvXq2zezMT0CK9B9gPcnmeZRAKFbLl0nYOdbCttb9BA9eh8D6LtQTrdmd/Fw/bkx8zlaVZ7K57HRYtoI8i+ZBdX549JVEL/ExHkysVp2Gcw176TqR/Lop8UVRXABtIhLAZVy1jEuRUiXwG2nWMvBVV5BUiOio15D44JDR8enXYmANjFTy3hLXlVJMuO47H/dWx7lsk5JqQgVNS/IDt3I44DOziRjRuxB6Gtkkl4h7m4RQti81QwvrYEr+HMg2IYGsWGiTT0+zd/7uAg1pH3HdnIIPJI5XsegNrp98MMMebBd5SAzzXVWrLdUZeoj0qb6u8UP2mkBsIokoOMEZxq6FxH/quJeMdOdy2WouU40VIq/ncKnyhSeD12djrPVU3NzrprhkQYnfRxD4bS2aFvl2HiIzzFD1TjCYuXuaMuqR2N89+0xrvPg3sr7K7tDPYREmAFdsa4lyrzn6fdtv0Kg3Lx/WynK0ZLjWlVi5zDmrhD54L8Dbotn0LZEITP+32QRvQVvHaqJuxC3UrSxaoOYcQUFC8QRJLZStecX5UGsprogvwUKfLLov6GGeDyJIb7rRKBYib3J5coC19hK57hp33Xlfw8WIykYoD3rSY1e5wdhw6pyBD2aK/ZuYcR/JaDWqG+7xHk39l/X6fXUnVD2ciTWVC7SlWKzqNaNi4GkG+8WfKLTiJuNLomsORAGYu7e+Z/cW7FFz/ZMf0y/WXzhJenI7YUTMWSxj3B0FzFIib807avoYBuPqYAtrjka05W063V1snz/H26lGzuqJ91z4y1ktGVzgCqJ+svvA9/cnqDN/jGvRTNbXqTqEFcBb4rtonkRXEDtljWJtlY/3U2GdYm8keFK65PZoZ6Q6Y6Y0vq+nLzvRZNX3Wmf5UTX/amH4QilGZXHrgNr9RAkDgiGfxntuPXuXyIjJYkIH1F1V4RKjXjsWz+jmg/+f+zPEx4+ClWcxVnVo6F8fGrWbKZBdrrtPKQKfWJObm0UOC7GRUWRW+kPhWI00EQXgslZb4VtIxbxmXZyOvNNSGwfFk7bPysjM6a0Y9tnkBNXGvTy9Pz0blPrHXu1Do/aREVZABKrC+G5W7VavrkHWLeWEZbj6umDsK+4pCdxVPuYWu5MPaJTtu6O8sXIT3KgA4YwcH7MjeDvj15QjuxW9evFgqPduO4UEQXQ0CnI6sKJv+M1rySBaURqnjIbwtL24+MqWkfGl5rrGkfw3X9CJVGl473VgpRJllVFZDcnvXA+dZgjcg9XvUn9sYKAruwrYL6lcQW3ILayizX62t4HPDWCEKxGuBsMwWO01lSwkyLYkmadeYBmaowraU/YdQ9wfmNY1Oomn4/+UDe0Q37zeNsp0HnbvaIIZRxyTNo44Bi6rzoMnCJzVxmx9M8j1tyG2mhpnQhjfGE0GAwaJkr72A0Kg0md9Y6wSMZXnujCRYJAQoBda8xrrEq7Hv03dOjrPVJlDrjV03z+gAqHd2303rMcJeHnrVTBdhlk7iKU1071e/0ckH1RtL3fnLeVyQtJZODodXMxHYlwt7qWEW3IuPr9/x64ub3959GLpQx/HxMogW81wbpJpBF+0WXwPuzGMFeW7jOcC9xfeAu/pEgpdenhUJDkUPeN+3goMifFZtoNvv01EZ55o2xQLjzy3+F8SgxNJD4B42JUMTdch0N1IFkZsJeqkNXqvpYg6p+ApHyoPTU6hiOgWMqmd+SY/7ge0Jc4xNLiwasgd/QFwq+WURK/AltvD7QMlhu4EBDI8peUByIZb2UGyzarzZxAAu4wu2T3jmXg7fDh0wH+d4QuScjrScbhk5d4d2f6P1nf8BTCW6Bw=='}
BUNDLE_REPLACEMENTS = {
    'eval_inner.py': (
        (b'active is image_nodes[0]', b'active == image_nodes[0]'),
    ),
}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['/home/user/Desktop/wood.png', '/home/user/Desktop/answer.blend']
INIT_MAP = [('scene.blend', '/home/user/Desktop/scene.blend'), ('stub_gray.png', '/home/user/Desktop/stub_gray.png')]


def _decode(payload: str) -> bytes:
    return zlib.decompress(base64.b64decode(payload.encode("ascii")))


def _materialize_bundle(root: Path) -> None:
    for rel, payload in BUNDLE.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        content = _decode(payload)
        for original, replacement in BUNDLE_REPLACEMENTS.get(rel, ()):
            if content.count(original) != 1:
                raise RuntimeError(f"unexpected evaluator source for {rel}")
            content = content.replace(original, replacement)
        path.write_bytes(content)
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
