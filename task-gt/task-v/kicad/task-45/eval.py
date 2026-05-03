from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


def _push_utf8_text_io():
    import builtins
    import pathlib

    orig_open = builtins.open
    orig_read_text = pathlib.Path.read_text

    def patched_open(file, mode='r', buffering=-1, encoding=None, errors=None, newline=None, closefd=True, opener=None):
        if 'b' not in mode and encoding is None:
            encoding = 'utf-8'
        return orig_open(file, mode, buffering, encoding, errors, newline, closefd, opener)

    def patched_read_text(self, encoding=None, errors=None):
        if encoding is None:
            encoding = 'utf-8'
        return orig_read_text(self, encoding=encoding, errors=errors)

    builtins.open = patched_open
    pathlib.Path.read_text = patched_read_text
    return orig_open, orig_read_text


def _pop_utf8_text_io(state):
    import builtins
    import pathlib

    orig_open, orig_read_text = state
    builtins.open = orig_open
    pathlib.Path.read_text = orig_read_text


DESKTOP = Path('/home/user/Desktop')
BUNDLE = {'common/__init__.py': 'eNoDAAAAAAE=', 'common/sexp.py': 'eNqtV0tv4zYQvhvwf5hqD5JaR9nt0akXKIpsD213F92iQBEHMi1RazYSpZJUEqPtf+8MSUcP27GzaA6OxHl9881wSAVB8IuQomIl6Av+2CiutaglNExprqCoFfwkfmA5FKLkGqLkTmQsT3W2gUvwL022hsvpxL/lqu1EVZ13L3pbxcl0Mp38qFhVMQVCA4OfhW5At2vNzXw6AfzTiAP/zRfATF3BPxBGoV38GsI4dDpWYnW0UUJ+Ri10v65LfJBtteaKAn2yMoyiOOR1uy75xV9tbXgOD8JsYLUMVsBkjg/LFXCdsYbrBD5ZR85qjT/TianvuETJe+vZSRQ3rZLoimkoypqZSyFNQumYfYWPW7Op5XRSWunDptYcGVXaAC95xaUhLsy2QZ7KcousuGSQrSAIppNCYbZpWrTokacpiKqplUHosjbMYL201yEXSIaXfy+3xMJ0kvPCVTQy/NHMibMYLt4CwfGkY5yPpIFOh53g+L3y6YDZcDB1c1Hye15aB4mFSD4aWEBqvSgbKPbLib4TTfqgI7/gXTWJxZRSMBINkKZIxDloScpZBXXRg9VPQJ/EV7cGBTe3R9A+bLD1cVnAd1ByGaFC7GF464Q1DZd5NEwo7nSOMYC2XdqFkLnNWtY5n8GGs9zl3uX8h+BlDpii2lo2jnYSFslvhxX5Wc0wYtYqLZCdbUeIKFBbSG2YzLiPS377+aEOCew+GSnfvL6dueqQ0K/AYuGwdy7ob2uhk063TtMlQ3bRsbSigza2sZ/IsfqOnbjPHTIwJm4GKGJtiS2EOwFL/L6WvMfmr11HOwZzgSwZD8nyi8kqQzvKzQvL5YA+3ICnKfTV9mjc+nO5D8viM7ZOLdHO7OnpOOc+rtUa9N0Tkh1/96xs+Uv5e4cprCJSh/vYtph1fn+FrYhd6Y07uiS6GBcq7pikxqUIgG5pn8kYN9y3J2j0a/Lmza3LJiuZ1rtd7o0pwzTFY86kaaR5Wcygmyy9ACRKNKIk6WhZ4PJrCrBzuNvRJO07cePC27iJ4fzGo+pk6NFJbpz27VCOnGSJ0Lph2ARj4x6ubxbwZijkJdlSU4RX4RzgFTYP8prVlR0QkbInG049zQoe7zs+noLtuiFo+ArDLGV4AOAJkJofsFnjNL/r89wbqWOqHZDhZPXM+bBvF88UQDGBbfo7tf61UrWKglZiHBwBeGhff3gX9Fw+V6wnsqPw8Aa0FqlLhLbxCKszDs4wdmdx3/yAEl2N3HH61Pu90GMOcbdwvCqMauqy2dsCwyoOz82ucX5T7biyxyr1gmodq5jhqhKSUc0oweCI92FucfiS/TQ+sfvrvePf2o9uAHtF8CU8vwzBqTKs2+JgGf6nEWRBLJcvJkw+mhPePfgdfX+HOETsKJlBaOyjoceAHgN6IhT299/kM8dT5NHMKEwcf9lsDL60CcIw+bMWMkLw8XlDrcsyOxfsiV53fRQcajE7APZmJd1kdgUR5/SKv9SNm7I7kmC5n8qB88FekZC0KN4j/GDi9mOr1zoEfL7XQK9wzGzpU48rkfWM1Xa+18NhEhIC5xhvFyEfvV937/OjVbcfeZFVig9Oavz+2xPzx4w3plfGw0PeQcGk6HvTX92nk/8AqENGEw==', 'eval_inner.py': 'eNrlWW1v47gR/u5fweq+SFjHsOxcX4zzAsVurl1c71BkN5+CQGAkKtZFEgWR3toI8t87M6QoSpYv2d1DW6AGEkvkcF6fGQ7pIAiuPvNyz7VsWQ5/j0XKs4vL71n48cPfljG7uGDvSpk+Mt3yVDAtG1nKhyODRUXGdSHrOct4oY4X6Y4XdbQIgmCWt7JiSZLv9b4VScKKqpGtZryupaY1amaHKq533bN0o+qoZjP4t2hgelHUSrQ6XM6Bwoz8Kos67F6yoq15JUKQV5QgLZqzYLEIosioodKdqHinwrudSB+vhdqXes7QcvNsSFNZVbJeKHFoOvqGt0rMWV7UWcLLEp9apWezT3/9+FPy4T3bsqDzWDD7+9X1FYycVWw2m2UiZ4kSD0lR5zKEh2gzY/BRsI5Y4xgYoDRvdRDRnBjNiTqzM4cYp0rJYeo2votYkQMnXmesFHWoIvZ2y9ZMlEqw5WJJS47+ktWrlhxWbonopAi3RExK8ZesXrWkHllZi85+eIK5otZh3YmvHa+aeK0sL6JvBcCuZmEr93UWHuI5WwMmzNtx8HZYDebsG8hzoYLnBIOYaJkUWahbAWjAARs3TJkadHMIsSRGfUODH9C513ZN2hcKgK15nQqwa3U3Z0q3Ec3gK9tuSU7PwjPN+cK39xdZCx9hIO9B78IObFYZdAc6AU2nKHXzt0tUoXuJ/ZeV/7K+84Vi/i52x0ZqcCa7MOzx4Rg7H1b8kNQyE0kmHsA5qJGy2kCxuO4YHVi9r+5Fy2SO0ipRa8XUjrdF/QBuYQD7BvJeszATWqQ4CUkCFhi24Ni1qT4UF5PPZQmEWG+6fAaFOOR7VqSa6NJaEwc3GoKEyIVWYWhR3z4MsOIWUoe8hSG4Y2+2LB5Pk8vAV/60c9khBKoFll2hwogAjXpYCFuvNTxD9IV5M2f0TM7p/fZjgUiB1Cgy9BhnqhFpkRcpUneuBO05GCJ1A17UvXfANKTycYtyAhicQC2M2ixDdAJMcYRSEUBqX4f6dZ8+qYFkkNSeiJNkHvL4AtwLs5WJEOvvxiTUxVuvzhvOCJp+LNRcPUJyb21Nx0QUDdXsLfIxwlBPqV1tF4dCaUVyPJPbhWhbiezzQO51s9cM2dDKHGsM45o94aLnYDayrZ3RiG6PPb9/FXrHZEMhAEGMK5YPnaPFAQGcL1rBs7B3LVYhGKftK0Qiu5UcUtFodkVfkBfIUUzrT0sZvW/Ykzir8HfADXsDTWD88F6ZvCrRpcBouoIG7/7xkwUCUjbQJbxAnfzz+gpWWJG0jbN4w2CG5Jp4mOguUpxVC96A57LQ2/JDZwPK2BJflGhWB3M33XClRLYNrRmFohAi0qKeCNoEqC5AhrAmjhnq47EBr+x5uTVczHA0smFFNqB132gHcHjZFuvoL7KHPD9pk+E2tAtrmXMaCmCAp6FoHN2cQRNUIty8sB269fqkqK/G443WbhVBdOfg1DFQ/SrHF9ud20vaXo2edwMUfsFSY9DdMJxrA8kd5BWkeim40lA23XYWUpNM0xXEsWhKEX1NsIFB0jGdCDXW0s4RpqROhplKOqo7wcqGecBpGsGXPYIHZscd269F8yuN7MJGhsbnDI2dkh1gztrqGE7b+/2GvccDDzOxvIBUMp3Ir/uamg0WUjMDHU/XmsAYuvkHDATxwpYI5rDijbsj5+2vKmYyQVWSTpUJt3WifziHirHySGiBO6eygRKiU/dZxtNO++OGXSefrq5/7rsRQgt2IUEcWA9RfLAZoOFVN2w8kWjRVkneUH7mDSUofE2UBCdi1Gu4joPXx9Brvw9zVkLRNM33wfyHBg8TPWhFLloBVAGOT7CzH4LjwWuTDtCnEAdjN9jSnl891ujoa3Q0/zuNmhY6glYfX1CIPqjU0VPq6JR6pVkjLmvLZTUw7YXlGKgjxukQRbPfpDpQNBtbyr9jH6FrLwX0H0rwNt2x+yNz8aDWZ4gMAAY1gx27F9HR70JInu6K0vTEzWbco3qxITI/Pmade5pGDjmR5r1wGPohTiaaX8++vDmZvofW7/F30HeAq5G66wl1h+aZudXvaQqY4eiHrAzdbEw00Vy8pnz2JdTojUcvlcg6UU1ZaGyq/O3Hq6U/cjixDWf6MnpS7ugAMGJkS2fgDgjevE0WPBX2BjVxYq5D3PnQWT/HQtonWLP6LcqVR4kGJvIRSEPLHnLAtr5zr9Ux6LF8z5DMJmtb1un9h61dH/2HQmRtOxMkPOVkcbfjrHC7yYqccE3HGWjY7K60feqNfJ7jpmRG4C2ajqnhvX0ylj/TIX4Fr2T+8zDOg63yTxv2SWpeUstgLnFwD46Xy6oyR0ScTUA63t7sq3Bw2+N1yt/USRghhit8JSR+op3olTE6LpbsDYvFxXqytzA0bMDJ+svcwTl2dBXXH2clbANYzbYgYBlP9xh/7hvRN+S8VFb3RQ2nmLdsyUIlK6F3eJkEZQKkgUKR50+I7Sv86XrDb2lqG6kKXXwWVshZr6JKoPp0S8tediOs79049tZfNlDVSwmNlitRAPeb1ZzdrOHvMkLAQjvfuvYVcEsccFECuxs2Yk/BzSqAenKzpv+XwbPdfUGLBAmRaPk1OzII8Pfz/8omPXURhVp1G+ErNjBh7o1AYee2IddU1rqo90MrX3M59/X3a+b62d2nu6Pwqbl+HAfXnKcGf0Eu4Il6bbhiDbe3MBNpMIDRlk3WlPVJCnirpqEfLzfsBo6nct9CH0m+Vv4JpAP6Pkb1bNqDp2m////GMmzgwU0c/I9C2OzPp5aOA/mp9ZT9JigbDCU3cQfk4WWZBfJA/lQ1BzSiv3oMnhb2wPSH6I2hOfSzwUkH2WG+v15zN+SJuZpWoflOsqKlu3L8MXMR0I05/hJi3IgXz95vmuaXV7cO4nUveZst6EfQpEnvbeyQ2eA2fnBl/+SMC+zle7ABr9tnvNRLZStojJ4IOehJGjKPc48H7naGAz7hT6R4bU0j9OTRmsjC1O0AAE8BxhOG0wU++ALTTiCwtQGj0e5l2P2xwMSLSMzjHDW0/QsNu7c5xc2KhYfn2fhEnGIOdXh0s3eeQdCxVLw9GmeZ59DWyWcIOsAlMTfqCRWJJKl4USdJMAgv/tbO24fPeLizP/p0Q5BvLLYgG8fasMBqFw6D3WsSzf4NdqtHWg==', 'schema.py': 'eNqNVG1u00AQ/R8pdxjMH0eAW/HTUlAjFCQkBFXafyWyFnuWmm52rd0NIgqWOAQX6RU4Cidh9sOx06ShjiXH4zdv3ozfOEmS8Wj+nYkFmrWwYMpbXDH4++s32FsEY5msmK5Ao11rCXbTIHClgQkBSGlrZjFrNpSn68aabDxKHCPXagUVs6wUzBg0UK8apW0fegm8RlFFJNHW8msHmsnNeOR+Fzv4eOQv8PYWy7sgNR+PgA7JVpiTTh1uG1euyuGLUiJE8EeDpXUx4oUpfFQSwxNW2jUTh3GrBGomS+LlQjELP/3DPYxUNpSlqGs4RCvkUBQULYrUoOCTKNIdNEq7Ng5+Obu6SqDm4CBZUAwoDELybvb+Q9LnNExbl3LDk5ttIGiXsPV5rvE2WfbgjrBrGGrjZHrRAx073ow1Dcoq5UmXMd3uEbTJ5JA9DO3p3AEfmcPNM32UeTf2p5NTyvTP/XY//Si5f18nudLtDthOhhTR+gnQ+cJfsm+qlqnPnzzm1H6nYlnLzF1RVwOvGotNwWsx9G/pDG5yELWxNwO3L8kFfmNS8hijQMFpmEpvpg4Z1aLWSgdX7lkW4DlNwbphXF3PL4EzKlqRz4HsXXXmvWi0alDbTe/l4M1gZXj1Bmpp84PBmPUqLTsbu29DSbgw9dDN5EQFqywT/ykgUKZPpDOl0tjT+fXNj6yIGxTQGZ1DGmA6hfMHDon1z7Pzw6YHq3s2oBl+CWgwK6Y3vRx6MYMKopYYl/uavBHXOtqkzeN9qNGebfsabXRJfD0AqW877pj/n2evObl4+UjrD/r0SvpNAJgvFp8WnQKfsbdUx17yKUrqOy0nR1bqs4y75OEE+AcnCfRs'}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('board.kicad_pcb', '/home/user/Desktop/board.kicad_pcb')]


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


def _run() -> bool:
    import uuid

    runtime_base = Path(__file__).resolve().parent / "_runtime"
    runtime_base.mkdir(parents=True, exist_ok=True)
    root = runtime_base / ("engiworld_eval_" + uuid.uuid4().hex)
    root.mkdir(parents=True, exist_ok=False)
    io_state = _push_utf8_text_io()
    try:
        _materialize_bundle(root)
        module = _load_module(root)
        func = getattr(module, CALL_FUNC)
        args = [_resolve_arg(arg) for arg in CALL_ARGS]
        result = func(*args)
        return _is_pass(result)
    except Exception:
        return False
    finally:
        _pop_utf8_text_io(io_state)
        shutil.rmtree(root, ignore_errors=True)
if __name__ == "__main__":
    print("true" if _run() else "false")
