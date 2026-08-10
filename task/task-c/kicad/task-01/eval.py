from __future__ import annotations

import base64
import importlib.util
import os
import shutil
import zlib
from pathlib import Path


DESKTOP = Path('/home/user/Desktop')
KICAD_CLI_PATH = "/usr/bin/kicad-cli"

BUNDLE = {'common/__init__.py': 'eNoDAAAAAAE=', 'common/native_kicad.py': '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', 'common/sexp.py': 'eNqtV0tv4zYQvhvwf5hqD5JaR9nt0akXKIpsD213F92iQBEHMi1RazYSpZJUEqPtf+8MSUcP27GzaA6OxHl9881wSAVB8IuQomIl6Av+2CiutaglNExprqCoFfwkfmA5FKLkGqLkTmQsT3W2gUvwL022hsvpxL/lqu1EVZ13L3pbxcl0Mp38qFhVMQVCA4OfhW5At2vNzXw6AfzTiAP/zRfATF3BPxBGoV38GsI4dDpWYnW0UUJ+Ri10v65LfJBtteaKAn2yMoyiOOR1uy75xV9tbXgOD8JsYLUMVsBkjg/LFXCdsYbrBD5ZR85qjT/TianvuETJe+vZSRQ3rZLoimkoypqZSyFNQumYfYWPW7Op5XRSWunDptYcGVXaAC95xaUhLsy2QZ7KcousuGSQrSAIppNCYbZpWrTokacpiKqplUHosjbMYL201yEXSIaXfy+3xMJ0kvPCVTQy/NHMibMYLt4CwfGkY5yPpIFOh53g+L3y6YDZcDB1c1Hye15aB4mFSD4aWEBqvSgbKPbLib4TTfqgI7/gXTWJxZRSMBINkKZIxDloScpZBXXRg9VPQJ/EV7cGBTe3R9A+bLD1cVnAd1ByGaFC7GF464Q1DZd5NEwo7nSOMYC2XdqFkLnNWtY5n8GGs9zl3uX8h+BlDpii2lo2jnYSFslvhxX5Wc0wYtYqLZCdbUeIKFBbSG2YzLiPS377+aEOCew+GSnfvL6dueqQ0K/AYuGwdy7ob2uhk063TtMlQ3bRsbSigza2sZ/IsfqOnbjPHTIwJm4GKGJtiS2EOwFL/L6WvMfmr11HOwZzgSwZD8nyi8kqQzvKzQvL5YA+3ICnKfTV9mjc+nO5D8viM7ZOLdHO7OnpOOc+rtUa9N0Tkh1/96xs+Uv5e4cprCJSh/vYtph1fn+FrYhd6Y07uiS6GBcq7pikxqUIgG5pn8kYN9y3J2j0a/Lmza3LJiuZ1rtd7o0pwzTFY86kaaR5Wcygmyy9ACRKNKIk6WhZ4PJrCrBzuNvRJO07cePC27iJ4fzGo+pk6NFJbpz27VCOnGSJ0Lph2ARj4x6ubxbwZijkJdlSU4RX4RzgFTYP8prVlR0QkbInG049zQoe7zs+noLtuiFo+ArDLGV4AOAJkJofsFnjNL/r89wbqWOqHZDhZPXM+bBvF88UQDGBbfo7tf61UrWKglZiHBwBeGhff3gX9Fw+V6wnsqPw8Aa0FqlLhLbxCKszDs4wdmdx3/yAEl2N3HH61Pu90GMOcbdwvCqMauqy2dsCwyoOz82ucX5T7biyxyr1gmodq5jhqhKSUc0oweCI92FucfiS/TQ+sfvrvePf2o9uAHtF8CU8vwzBqTKs2+JgGf6nEWRBLJcvJkw+mhPePfgdfX+HOETsKJlBaOyjoceAHgN6IhT299/kM8dT5NHMKEwcf9lsDL60CcIw+bMWMkLw8XlDrcsyOxfsiV53fRQcajE7APZmJd1kdgUR5/SKv9SNm7I7kmC5n8qB88FekZC0KN4j/GDi9mOr1zoEfL7XQK9wzGzpU48rkfWM1Xa+18NhEhIC5xhvFyEfvV937/OjVbcfeZFVig9Oavz+2xPzx4w3plfGw0PeQcGk6HvTX92nk/8AqENGEw==', 'eval_inner.py': 'eNq1Gmtv2zjyu3/FLHtAJUQVkvb2Hl6ouUXaxRZ76AFucffB6xMYiYq1kSktSSU2DP/3w/AhUbKc1L1uPzQ0xXlwXpwZkhDy/oFWLVW1gKIWcF9mNH/1GoKf/vPu8gpevYKcKSY2JS+lKjMQrGCC8YyBYK8o57Wiqqx5GBNCZoWoN5CmRatawdIUyk1TCwX9MjmzU5l8cMO6mxTMjeROGmRZXVUs06AO203dcsXEbCZ3Mm6oWscll0yo4DKC2s78Vpc8cD/yUnC6YUGaFmXF0jSMgMQxCUNDQmZrtqEd9jXL7hdMtpWKAEVjxo6bzabmsWTbxq1vqJAsgqLkeUqrCkdCqtns84+ffkk/vIMEiBUpmf38fvEeEjjJ1+zDxw+f03cfFt4ivRMEjICUvFR6LQlnn35+//7zJ0hgSeSaMXUVazKpzNYkAjP3emLujTe3ms1mOSuAbZWgmUoFK2Qgs3Wq2FbNQSoRwqu3UJVSLfMyU6v5DACAELJgqhVcf4G6gL1gRQTbCHYHbUTsgYkdyN3mtq6g5FJRnjFtIQgv6lpBYiTXkQv1J7nbSNzTSv9CVHK3gZJ38g0QGPeicZPQcIT/ygIqxgO524TwFq6A8hxK6Yjj/PJqFelN9UD4L6u5KnnLuknBCkjgY837KdwaJHAZX0b4XzePHDbIn9xthljLwqfeRFpWoeaqMf8vL1eQJEAaUTdMqB0ZIvD21ITwNoE3FuzKgC2cI07A9btolq9XX8kXVc9yNE1Zid30By1JSKCoaqoC3El4ct3OW/f6xDq2zVijIPi8a9h7IWoRwb9p1ZpxeJqHhkrp241gxXAxmmFMm4bxPNgTwQoyB23iZEvmaAxkR+awOxi2hHEGBHIOZUIqC+pWNa1K81L07tQHFUNUQOLNBYrK+7TMExtA0GJZo70+6bGFMw36Av5Z0xwwLpS0QhYlqBruef0Ij+syW8MjEwyaPlSzXANaCO3xacNEqmPDHNDLl1KJCCRTK0hgfxisxz1Or++DhAemHRhXphjo0E9M2PK8FkMaBrpxyHOhMPIQhL7SeK06CLYtpZJBh2ykexEztAi0KOJkhQKFTSllye/msO9AD2QIanQrusnHUq2hbhj3qAGVMLIgDGlILxaM5kHPuA1wg4jbh7/Tol72UkD5alsbQwyVOYLYy6U25JVRio1ZEiVJromWJk7ZRYeBfRm7M4owZK0lah5pVc099ffh21900mY8a7HaMOvGx8CTVlS300bUO8w5ZuSwjaxoyJ4LD1NoJ0+V3nA6/N/Ubial/ZTZjHQYs63SG9ptZBdedDYEV3P4saqGZoBBRTKuTAiLM1zYCcVLooKOHjKREFpVVoKpxUCimR+YWZ4EeMQMxR3ikXQZ9kvZtmGZYnlibKH/QDPV0iopSO/cQ1QHgnofGRurJANkDoZchUbARwDz2VGEGIjs9Rw+1nBtQrJgG1py/f33lknMZrUG0cSP3XKkF+ehnneuzhU6r9OWdyeApn1C6gP+Tgv98kjex8D9El4rlkglhguW8+9XIe5uKBOjiaxilPc6cLKtN02rGKg1G5UlVMryjm8Yxyri97YULIfbnV6IyY5odQ0RazytZDlGHbIgczznAiwIbtz44KeeWiHTETnGM57JwIsSXr6Ka0fhg6oMA5RgcdFWlf4ZCBIsFzerMPg1vwhJhGBWx+E4a9MAxzkNbmapv8V3om6b4CpcxTTPg5KrwJ9/HVpb5myrUt5ubhmeiPtGsKLczmFDt4GZlRHkrKBtpZLLEC7gyqS5el0Edg1uEmnHpWIb6cTmDCS93R2Hez1SbVMx81und/aPycz93KFDlcmHVNSPZx0IR3yMT8NDt9RzDO2PvSN+wUlcFp1TIsSeLK6x0rq5JofVpFnUQrE88GhGcM92SUU3tzkFlOUcAvyzJDuyisAMt2QVjk4jow4T0y0Hy8thqv+4xhzHU/fSAK2c7tzvY6uaArpI4Go2XPSYmiqjINaMDvsJyFFK5VPWljoBEs7O5uZJlS8DZ75aXFsUrR7tyCpEg7B7mcboLNBFWu/Q9102cljC0fn5Zg7v/YpYKrqTQBWUSkItyruS0wqaWpYYpH7Q+brORUp+Z04QhACqFM3WNoN/gYk+hjeJLmAQR7qA4+zRABV1VdWPehHGRCbRxIdhsxY5EyYq5qIsrA+ckXbhSUUxY9kH0snVSHUOTx9tkw51GJfzHYkQvkv8mdM4Ro5i9+V0V5B9v/Ywz9umKjOqnAg7LZBwyn+fDwlD4uZwxLTU7SO+YyoIJqzwKOD3hjUOLcf+6kxVp4hP+IFH3YWMSZcYMoNH8pM0e4TjTVgBfNfzdYzoSQ39I9gj9pfbl6tDZIa7l6tDON8b1Ifvkr1DfbBKOyMzGrhD2jcqU8rz1PmgrawwMRQPLD+ROtltnJs0ObCJdMl+6hIl56KjZNXjaRx5/jyHz7WilbPuDHun0PJsTfkdy4FmopYSEJVX3enKVmm4BGS70dsblB6mjjlRr4ehrV7CE+2dLh6YgBK6arGjOfZzWlVna9bsONU7TrsdT+jOI5x4W5/SYP/1SJUdlmlFfG9KqIWJzFQwzKOYKDMIeA2La7M9LI6+uDAwvnZL8xTzuCWexLgU/5a8R2X6W7FUVCiJRWhAFsQ0/LD2FSy2qejL/y5+zS/+9DLC9WGPPTsT+80J7DdH2M8sG7UXYu68S7v06YQvaqkYT9S8uLnsXO+0iC48DBOOqlct529WcGFEhmPtsuYT1AIs+d53T5Q42lz+osvH/nASrMiZPOGughXGzNFu7O1I8Kz5GIvrSCAstvHnkHHlVB3pHyX3SLh8HzeHH9/C1eErytGObmq2diqmduydHVZ7yKnIWmYqwPaTt87tLNTKMwG3l47RG9dKkSe09tc5fGSPzslbybpiCX2BVhgVd6DoPePa7fFyq5RlzU1zyE/7wq7i1fdfYIN9nxYutF3fOAozWxOkAhNlqWvZZcl1e02Xtd2C7KkFz+d8XhB4vu84qoBN9duHG131upBwVO8eJwr9/voKt6t6R4fNmNjN1xDLniH2QuvbZOjruq1M0KsfmKhoc6xUqDnr+qd2J+h2iHtaMM6Lw57y7InzdKJ1NBXfO6yHjpnsJDM3fxAzN9PMvIDPa6ZrmL6l00n3VpskFjQDsUqm4F8LbOlXcEcbaRH9wnagY9IceO37svPEDDWFWdBt/cB+gN9aqQyApo/K0if1WzAXfkZhqanh0W1MMd/r8uwcRdiqVqam7HhgOu/kNU91bMhLfnciMg6YwRtPc9DhFSnXv1APXMfu4Up3HI6mky7rcpuZirUm6bS8RkOxkqM4jJF2QGY5v7pc4WkakDiOiSvyjvZydWnjLRkHb2KD6wZ1dcs6XqDkit1hqNVeN8XYOFr/zUTrG4OwQ2RSF/6qU4AGyk7rPvs63Wdfr/vsi3WfTes+O6n77FvqPvsC3Wdn6P7mm+n+73P3KIXFmXwAc/Oj5bOmErJaCDx114zm7nDFJtBzd0zER0q6q4OJOyaHzWtWfJHteBmxJaW7U8dXKZ7N/EQryaLJ1lYy5DiaaF5guoYJYcv9ZNuG/mFnoL/i6rY3ccVle7k6+8rkQ/yuzNRCCzoovBNlTWVq5Q+Jtu17tOgAwZeXq/ie7WwaqhFqm9kfQvOICVfahzHYNLllRS0YjmihmPC763+Y1D+L9qTQpwGdvCdk3Y27K7nLkQXrs8yUBq6jWO0GzW1TEEsfle4GXL8ylVyX0A0v57vbGdM7SGD4+uXpbPH/uOI/47L9qYvTL7s8PbXbC9P/uJq+NPeu5L6NQRklYrbk39dN25fJAupHUxlNMB+esL6JpZN22OF/xhKvRpZonA2Lm3bDdTg116ARaOfTM3jAmtkOH9bHFhT7DfWjKTXqR53DoIsPnyqI+lF3Mz3nvibhaoDPEHwanY/KRIcIz57VN1Go4c3wkdpT5Ql19jKY6F1oJEdl8KlSeKKP4TBfjFAOgcxRazVh8258zEBLDtdOh321cyJOGdL+3Z1rTAyIBZ3ou1hNwmhKt4NpT09DHx7puGdtNnmpkxmePO6O7ny+jWPrqofJdNRu7iucE0ZxJMZkcgOn7MFmqVMgMauYphyE4aTVWNgRB9NgTvP9W4juGVxq8iM5fgqHD2Njoh/EYTOmfwo38XZu8Mxu31El9qkcPs6L7RifhmZoMjinRxEQI009ZYaRhwN7tgaD7t4C0W/F9IweeWuN/skclgOB7QlqnMwhi82VYE8wcwSBOCXoWfdjKHkgRtp6iRlGyGHFBNUPPSGLu18RdqOUJVsrdjhyhEy7gbXa7uvK25BsNxsqdkZYZhxYtR5ms1lZQKpP5TTVL0LTFN+xpKl9F9orSF8ByZiKuwd8nto9xTVT5j2uSepjYhtR2GaYUnXPRzj7H/8xPzY=', 'schema.py': 'eNqNVG1u00AQ/R8pdxjMH0eAW/HTUlAjFCQkBFXafyWyFnuWmm52rd0NIgqWOAQX6RU4Cidh9sOx06ShjiXH4zdv3ozfOEmS8Wj+nYkFmrWwYMpbXDH4++s32FsEY5msmK5Ao11rCXbTIHClgQkBSGlrZjFrNpSn68aabDxKHCPXagUVs6wUzBg0UK8apW0fegm8RlFFJNHW8msHmsnNeOR+Fzv4eOQv8PYWy7sgNR+PgA7JVpiTTh1uG1euyuGLUiJE8EeDpXUx4oUpfFQSwxNW2jUTh3GrBGomS+LlQjELP/3DPYxUNpSlqGs4RCvkUBQULYrUoOCTKNIdNEq7Ng5+Obu6SqDm4CBZUAwoDELybvb+Q9LnNExbl3LDk5ttIGiXsPV5rvE2WfbgjrBrGGrjZHrRAx073ow1Dcoq5UmXMd3uEbTJ5JA9DO3p3AEfmcPNM32UeTf2p5NTyvTP/XY//Si5f18nudLtDthOhhTR+gnQ+cJfsm+qlqnPnzzm1H6nYlnLzF1RVwOvGotNwWsx9G/pDG5yELWxNwO3L8kFfmNS8hijQMFpmEpvpg4Z1aLWSgdX7lkW4DlNwbphXF3PL4EzKlqRz4HsXXXmvWi0alDbTe/l4M1gZXj1Bmpp84PBmPUqLTsbu29DSbgw9dDN5EQFqywT/ykgUKZPpDOl0tjT+fXNj6yIGxTQGZ1DGmA6hfMHDon1z7Pzw6YHq3s2oBl+CWgwK6Y3vRx6MYMKopYYl/uavBHXOtqkzeN9qNGebfsabXRJfD0AqW877pj/n2evObl4+UjrD/r0SvpNAJgvFp8WnQKfsbdUx17yKUrqOy0nR1bqs4y75OEE+AcnCfRs'}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('sheet1.kicad_sch', '/home/user/Desktop/sheet1.kicad_sch'), ('sheet2.kicad_sch', '/home/user/Desktop/sheet2.kicad_sch'), ('sheet3.kicad_sch', '/home/user/Desktop/sheet3.kicad_sch')]


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
