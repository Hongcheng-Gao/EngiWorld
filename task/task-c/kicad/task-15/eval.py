from __future__ import annotations

import base64
import importlib.util
import os
import shutil
import zlib
from pathlib import Path


DESKTOP = Path('/home/user/Desktop')
KICAD_CLI_PATH = "/usr/bin/kicad-cli"

BUNDLE = {'common/__init__.py': 'eNoDAAAAAAE=', 'common/native_kicad.py': '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', 'common/sexp.py': 'eNqtV0tv4zYQvhvwf5hqD5JaR9nt0akXKIpsD213F92iQBEHMi1RazYSpZJUEqPtf+8MSUcP27GzaA6OxHl9881wSAVB8IuQomIl6Av+2CiutaglNExprqCoFfwkfmA5FKLkGqLkTmQsT3W2gUvwL022hsvpxL/lqu1EVZ13L3pbxcl0Mp38qFhVMQVCA4OfhW5At2vNzXw6AfzTiAP/zRfATF3BPxBGoV38GsI4dDpWYnW0UUJ+Ri10v65LfJBtteaKAn2yMoyiOOR1uy75xV9tbXgOD8JsYLUMVsBkjg/LFXCdsYbrBD5ZR85qjT/TianvuETJe+vZSRQ3rZLoimkoypqZSyFNQumYfYWPW7Op5XRSWunDptYcGVXaAC95xaUhLsy2QZ7KcousuGSQrSAIppNCYbZpWrTokacpiKqplUHosjbMYL201yEXSIaXfy+3xMJ0kvPCVTQy/NHMibMYLt4CwfGkY5yPpIFOh53g+L3y6YDZcDB1c1Hye15aB4mFSD4aWEBqvSgbKPbLib4TTfqgI7/gXTWJxZRSMBINkKZIxDloScpZBXXRg9VPQJ/EV7cGBTe3R9A+bLD1cVnAd1ByGaFC7GF464Q1DZd5NEwo7nSOMYC2XdqFkLnNWtY5n8GGs9zl3uX8h+BlDpii2lo2jnYSFslvhxX5Wc0wYtYqLZCdbUeIKFBbSG2YzLiPS377+aEOCew+GSnfvL6dueqQ0K/AYuGwdy7ob2uhk063TtMlQ3bRsbSigza2sZ/IsfqOnbjPHTIwJm4GKGJtiS2EOwFL/L6WvMfmr11HOwZzgSwZD8nyi8kqQzvKzQvL5YA+3ICnKfTV9mjc+nO5D8viM7ZOLdHO7OnpOOc+rtUa9N0Tkh1/96xs+Uv5e4cprCJSh/vYtph1fn+FrYhd6Y07uiS6GBcq7pikxqUIgG5pn8kYN9y3J2j0a/Lmza3LJiuZ1rtd7o0pwzTFY86kaaR5Wcygmyy9ACRKNKIk6WhZ4PJrCrBzuNvRJO07cePC27iJ4fzGo+pk6NFJbpz27VCOnGSJ0Lph2ARj4x6ubxbwZijkJdlSU4RX4RzgFTYP8prVlR0QkbInG049zQoe7zs+noLtuiFo+ArDLGV4AOAJkJofsFnjNL/r89wbqWOqHZDhZPXM+bBvF88UQDGBbfo7tf61UrWKglZiHBwBeGhff3gX9Fw+V6wnsqPw8Aa0FqlLhLbxCKszDs4wdmdx3/yAEl2N3HH61Pu90GMOcbdwvCqMauqy2dsCwyoOz82ucX5T7biyxyr1gmodq5jhqhKSUc0oweCI92FucfiS/TQ+sfvrvePf2o9uAHtF8CU8vwzBqTKs2+JgGf6nEWRBLJcvJkw+mhPePfgdfX+HOETsKJlBaOyjoceAHgN6IhT299/kM8dT5NHMKEwcf9lsDL60CcIw+bMWMkLw8XlDrcsyOxfsiV53fRQcajE7APZmJd1kdgUR5/SKv9SNm7I7kmC5n8qB88FekZC0KN4j/GDi9mOr1zoEfL7XQK9wzGzpU48rkfWM1Xa+18NhEhIC5xhvFyEfvV937/OjVbcfeZFVig9Oavz+2xPzx4w3plfGw0PeQcGk6HvTX92nk/8AqENGEw==', 'eval_inner.py': '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', 'schema.py': 'eNqNVG1u00AQ/R8pdxjMH0eAW/HTUlAjFCQkBFXafyWyFnuWmm52rd0NIgqWOAQX6RU4Cidh9sOx06ShjiXH4zdv3ozfOEmS8Wj+nYkFmrWwYMpbXDH4++s32FsEY5msmK5Ao11rCXbTIHClgQkBSGlrZjFrNpSn68aabDxKHCPXagUVs6wUzBg0UK8apW0fegm8RlFFJNHW8msHmsnNeOR+Fzv4eOQv8PYWy7sgNR+PgA7JVpiTTh1uG1euyuGLUiJE8EeDpXUx4oUpfFQSwxNW2jUTh3GrBGomS+LlQjELP/3DPYxUNpSlqGs4RCvkUBQULYrUoOCTKNIdNEq7Ng5+Obu6SqDm4CBZUAwoDELybvb+Q9LnNExbl3LDk5ttIGiXsPV5rvE2WfbgjrBrGGrjZHrRAx073ow1Dcoq5UmXMd3uEbTJ5JA9DO3p3AEfmcPNM32UeTf2p5NTyvTP/XY//Si5f18nudLtDthOhhTR+gnQ+cJfsm+qlqnPnzzm1H6nYlnLzF1RVwOvGotNwWsx9G/pDG5yELWxNwO3L8kFfmNS8hijQMFpmEpvpg4Z1aLWSgdX7lkW4DlNwbphXF3PL4EzKlqRz4HsXXXmvWi0alDbTe/l4M1gZXj1Bmpp84PBmPUqLTsbu29DSbgw9dDN5EQFqywT/ykgUKZPpDOl0tjT+fXNj6yIGxTQGZ1DGmA6hfMHDon1z7Pzw6YHq3s2oBl+CWgwK6Y3vRx6MYMKopYYl/uavBHXOtqkzeN9qNGebfsabXRJfD0AqW877pj/n2evObl4+UjrD/r0SvpNAJgvFp8WnQKfsbdUx17yKUrqOy0nR1bqs4y75OEE+AcnCfRs'}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('board.kicad_pcb', '/home/user/Desktop/board.kicad_pcb'), ('cap_models.csv', '/home/user/Desktop/cap_models.csv'), ('target_z.csv', '/home/user/Desktop/target_z.csv')]


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


def _apply_runtime_env() -> None:
    os.environ["KICAD_CLI"] = KICAD_CLI_PATH


def _run() -> bool:
    import uuid

    runtime_base = Path(__file__).resolve().parent / "_runtime"
    runtime_base.mkdir(parents=True, exist_ok=True)
    root = runtime_base / ("engiworld_eval_" + uuid.uuid4().hex)
    root.mkdir(parents=True, exist_ok=False)
    try:
        _materialize_bundle(root)
        _apply_runtime_env()
        return _is_pass(_call_inner(root))
    except Exception:
        return False
    finally:
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    print("True" if _run() else "False")
