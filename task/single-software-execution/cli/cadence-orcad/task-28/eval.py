from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


DESKTOP = Path(r'C:\Users\user\Desktop')
BUNDLE = {'eval_inner.py': 'eNqVVE1v2zAMvftXaLrMWht3K3YYgrpAgHXosRh6WpypqkW7Wm1ZkOQiaJD/Pkq2EwfFCiwHOxIfHx8/zMp2LeG86n1vgXOiWtNZT4TWnRdeddolyXj3x3V6+m8hqYKnEf6pUY+T2x0ek+T25ucNyeMhRWrVIDHLLLiueYGUZUZY0D75vrq/4RFpISu71iAwtXS9WvzarMXidbO73JOTU+HOCrn7co73hSzk8vDA4+7rnrLkbnV/+w/OwLG8WP++uv5Y0MJ92pwhPkkkVITrzraiUa+Qetj6JXHeMrK4Du9lQvAXrpF0lJy5/jGlV+F0Tc+jkc1ho4oIa0T7KAVpl0M92qy2XW/Sz4xlWrQw97aATdDxAqtlGlFCSgtbaIxB8cky1KNMOsmGF9Hwrvem9y4d3lwqe5QvVekH/YN1asoRO2tLxAntEDSiLwg1rs/81tNorANBbC5aQhpacm97/0TfQFF+mIec7KgRztEl+SEah9nSY2wahY5i2D76qYrg4AUZGWyVw7zYkMCRdE0tCBxFukH6isLWQOlBTqJb5ZzS9ZLsAkko8Z7OGGKFB6Ip4Kz7wQXZMS3sQQq67CRy5bT31eIbdgGs7azLqarRByhj5EM+9z8Eqv1/8US/9zPFOkrnRflMeidqmCosVVWBdSR+jYdarJoGsEHhAkHv5T9Fil0Kce5tDyeW8gnK58G2pg9j2MULwX4/HIouPMIcEZUHG5fChRQeyFSZuEnoJnmrAbcLdoCHPuH2yTFPzluhNOd0KMe0kGyNa8NBMoypQTXTVbaydd/iRrkLJztNssmElFyMtnQ+eCPC1mHYERhpAtSNzsYqdAkLL5N9a1x68qkFYDb7hs6J0hJj5JfYWe3CIhWuVCqPM89Y8hdE5r+t', 'ground_truth/manifest.json': 'eNqllVtrgzAYhu8H+w/i9bC0OzB2ZzXrSm2VxJ0YI0RNW5nWENPSbuy/z8OQlWVo3FUw3/e+z5e8oh+nJ5qmL+OE5vqN9lI+adpHvRQFRsS62NdXlAeUD5wh9l3PWAVcP2t6xIHRsmcC4BjAHwWeJVWhVun1/udZG2OEJwtbmVGpOjPOMZpOhsqQWtaZclG2j5Qptawz5RJ7j1AZUqk6M67w2PWVGZWqK6N4RTByHRvAuYlmqqxjdVdmMd4/mMdqlXN6JvJB32M2YpVT9iYeiZWynDozZEEAFr2ybNRKWfZmHqtbmRGPk2TAxNqIeCLhLCxsw6njSEief9fRftPLf9EFELNwdHk9NPapzH3qWWVVdk2tziwO31hCQjrYH7DImBHmOwni6VkevJp/kAkV/yJk3523IoIs/cN1XKh/21roodUzFyR82zLMKcu4MMReSOyRb1qze0+CgMBzYfunlOQ5TYPkYLBoKfE3EQLzsSO7Gs++bXWHwLTn4I/Z66IsVPDUDF4ur1WLTni4jncUb0hataVks12SUGw5Nd5jVhvpEc3j1aZpeoDg9rsSZIRHxXXuqlzKf/LnFyiDBIU=', 'ground_truth/psu.txt': 'eNqNlt1y4jgQhe9TlXfwAzgzUkuyzZwrsPmZBBjW4feKIgMzS20CKcLWVt5+TxtCyGRmdquaWFKf/qRYLasHi+XTfvH1r2j0tPi+isrV43a3v7woPn28335d3P+z3f31sbn5vmbjfvnxw/7hcb7dfV0s54+77d3Kysfl6mH74W63vLzobTdR/XEXSRrZ2idT++RdJEaSy4vLi+F2v7iPBi+Tfd7wufm6erq8OI31Fw+r+KArVk/r75tXVdxd3+0Wu2cC9n9eXlifz297Q5vFtiax9qeJL2NJtJ1pW90i0yQr48RzVEwVIT5OaoZ9b6aBEY7NxEytMWWcHdu2Ck781IYy9irWNsXW+mMnO0iyqciRz7ZKnK4glan4Ay9NqmYV2PpcuBpXMejGquoPutaHsrASrmy1kFtjw9SIKfNhnGbVgMumJlQD1ko1klCSBh059DMz5U/7Osfg7WbePUe3zw93W32h39ab9X693TDoMFS97rcvf7DePEWPq90x6rV/2A/tR/2/H+5WO+5bo1332bxRpFdhWrsKvV78ui3+sDN1i7qg7lD3qAfUEzQsGoKGQ8OjEdBIkFvkgtwh98gD8gSFRSEoHAqPIqBI0LRoCpoOTY9mQDNBy6IlaDm0PFoBrQRti7ag7dD2aAe0E3QsOoKOQ8ejE9BJwDT8ozUIwlVb3fVebz7sNEtd+UsC0ayHDbAJbAqbwdYgBmIhAnEQDwmQBN7AW3iBd/AePsBzMIXP4GsIBsEiyHFOJ3Mnea6va5rqq/oxS22iiVSDNbAWVmAdTgs5TCgpJIPU4AychVM2N8H5QKy4qTiCXxOd41Wy6yaQWq9Ve8F/5Xw/6inqGf26UaqjghPXOXOdU9c5d51voW5VQ4CyKpgCFFfxFKh4RSpToUqtkBW7AlfkCl2xK3hFr/DK1+wgXTOE3PMsaaRoZGioRDNIdRQR2CCvQVzDanJRRVaDKE0rovJalV2knWdYniLP6NfUUx0VROVE5UTlVrOSEquaWpWPRGlOknOel0WKIkOhEs1Z1VFEVEFUQVRhNZ2pIqogShOZKE1mos4TupmimaGpEk121VFEVJOoJlFNq+eAKqKaROkJCC8ngEeBvBbDWpS0KGlRcjwS9LweC0ralLQpaVOiZ+R0QHhYqO1Q0qGkQ0mHkmtLM7hmS2hsOVx7XAcO0yXqpoNLvWbUNaOuGXVjaQY3QuPD4cbjJuBGPXSJuulj1A2jbhh1w6iupRl0Bd3Av2xxzKHrOUyXqJs+RnUZ1WVUl1E9SzPoCY0Ph55HL6CnHrpE3fQxqseoHqN6jOpbmkHfox/QZ19o7DsO0yXq5pDVfspfxl8NA4uB0AwGDgOPQWCHY5QMKBlQUlqUQjMoHUqPMrDDMUpKSkpKhhZDoRkMHYYew8AOxyjh55O/GkaWZjASGh8OI49RwCjBKMUow0gl1IjqKOI6R0yVEVNlxFQZETUiakTU2NIMxkLjw2HsMQ4YJxinGGcYq4QaUR1FRI2JGhM1JmpM1JioMVETSzOYpJhkmLDvMBEahzwmAZOEfmpEdXQQNSFqQtTEqo+BRE2ImlmawUwwY4eEmcPMYxYwSzBLMcs4qhr9UUTUjKgZUTOiZkTNiJoRxTvty1Dc3DqJTze7i/nJhqPTijVlK3656IVXs7pYsNx+GVgz5zdTv8z6+XxXAFijNcCB5BGQIEWG6jvNL/utAvxckgrgr7wijtWCj0Py88DzD/wvr6Qj5ngl/Rbz/mJwDs7DBbgELoXL4Gqn9SY/X28S8+3953oPF9LPL7V3pdHhUvuR+atrlbvI5bnT8sJVtSOnysol/3d5v7+4f/+6NJeyfmM+lvhUyGXvJlaV9f1G/FrhWf9/dvvdhX1WFjJ5Y/w6I94o5aDsXGn9aOK31aTWk/SWc+ONxOd1pWhleUj+217OyjHE51WmVHXmi5/3iEnitzXni9fnzbLe+5zHb0vQ13egRT+r3C/D5qeXInT9Us5HD4vn6G4VPWyX62/r1TLab6Pd6ttqt6I3ejzWpE/RdhfdL55ZbUbUVe59tP9zseGfVfR0gC42y1NEtDyVuU8fdPp/AS9MHd8='}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('README.md', r'C:\Users\user\Desktop\README.md'), ('demo.brd', r'C:\Users\user\Desktop\demo.brd'), ('project_meta.json', r'C:\Users\user\Desktop\project_meta.json')]


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
        shutil.rmtree(root, ignore_errors=True)
if __name__ == "__main__":
    print("True" if _run() else "False")
