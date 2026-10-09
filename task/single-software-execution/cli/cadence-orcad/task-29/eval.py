from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


DESKTOP = Path(r'C:\Users\user\Desktop')
BUNDLE = {'eval_inner.py': 'eNqVVE1v2zAMvftXaLrMWht3K3YYgrpAgHXosRh6WpypqiW72mxZoOQua5D/Xkq2ExfFCiwHOxIfHx8/zAq6lnBe9b4HxTnRre3AE2FM54XXnXFJMt79cp2Z/oNKquBphX9o9P3kdoPHJLm++n5F8nhIkVo3SMwyUK5rHlXKMitAGZ98Xd1e8YgElZVdaxGYAl2vFj82a7F42uzO9+TFqXAnhdx9OsX7QhZyeXjgcfd5T1lys7q9/gdn4FierX9eXL4vaOE+bE4QnyRSVYSbDlrR6CeVerX1S+I8MLK4DO9lQvAXrpF0lJy5/j6lF+F0SU+jkc1ho4oIa0R7LwVpl0M92qyGrrfpR8YyI1o19waFTTDxAqtlG1GqlBZQGIxB8cky1KNtOslWj6LhXe9t7106vLnUcJQvdekH/YN1asoRO2tLxAnjEDSizwh1fZv5rafRWAeC2Fy0hDSM5B56/0BfQVF+mIec7KgVztEl+SYah9nSY2wahY5i2D766Yrg4AUZmdpqh3mxIYEj6ZqCEjiKdIP0FVVbq0qv5CS61c5pUy/JLpCEEu/pjCFWeCCaAs66H1yQHdPCHqTKlJ1Erpz2vlp8wS4ogA5cTnWNPooyRt7lc/9DoNr/F0/0ezvTUN9WwF8iQfxBsqnEUleVAkfi53goxqppFHYoXCDorQJMoWKbQqBb6NULS/mgyt+DbU3vxrCLR4KC7g5VFx5hjojKK4hb4UwKr8hUmrhK6CZ5rQHXC7aAh0bh+skxUc5boQ3ndKjHtJGgxr3hVDLMqUU101W2grpvcaXchBNMo2wzISUXoy2dT96IgDpMOwIjTYC60dmCRpew8TLZt9alL761AMxmH9Ep0UZijPwcW2tc2KTClVrncegZS54BYmzAPg==', 'ground_truth/plan.json': 'eNrNll1LwzAUhu8F/8PI9ZB+xKLejRVEBL86QREJtUk12KYl7Qoy9t9NutVkkNEwDOyq6XlDnvck55CsTk8mE4BJRzPSoLLCNKcEg6vJmxSE9ByA6TAM1RCqYQTk6L3/B3WKmzbNvlFVN2qV1eYjdJaWRMRB94W8OkBq9d4Fpx3BKOdVqeboEzgtClRK0TsLVFxAEa+WDA8aPNfEIm37jMArabTF0rouRKqIkxwT6VWmulHX0zHb4THZDq1tw2OyDa1tR8dkOxps61VP2b6C3ykvDUiZjM18LcZIK2Pxowd2bPcNtds0+3ZuhBaYaL4rWmiiJR56cAWEe4B3joBzw+nNb53lNw+MOFfZxYbs7uPFf9BC2064GKGFh9KMnXDpimbsBN9zhDOWZTJaJ1Y4aHdyyc31bAQHbXCRHW7xEo9tZnQoLjDifFc4Q6k8OcwOGnHW2Wl3YLMsy5T/iGlb+N+rkhT0k34U8kqHw6txWLVBGSfbu1eJlIl4xTrCN4ofSUXQ1r+9uluu', 'ground_truth/sum.txt': 'eNqNVltv4jgUfq/Ef/DLSkFKQ+4BtLsSBWanmlIQl+3sU2USF6wmNuOYdthfv8eOQ0KLVtNKVY7P7Tv3ro5FgcUJTQR+p2yHluTAhezcTIa9nKc4f+fitTdlOwofedZzZHF45iLF2fNB8C3x/F5GCu5sRda5mXGGRgeB/AR5g6E7GIYh8l0/7tyAPWN/JbGkpaRpOezcIPipGdOfkjBZIvT9wbr1o9BJIj/oIvSPIt3EiQehIr9vrMCLnb7n+Yq5sfxw4AzcqN815mhBWEk5KxFlqKB5Dg+SiBK9U7lHIcpISguco0OOU1JWSg/4BBJDhNZc4twKwfKSHyXAspSXRY4ZKeHTuCAl3TG03tP0Fd5Bz3WSwIv8trtKdIHTV7wjaHUqtjxvPHh+DHZnVAguSGbFCVDTYkuyDChXuaSstLww9ozPGUn3mFEoyCdbQdvSWTcwil+4KLD8DKCOZTnWJSFDNN+s0fwLmozW04Y3VXZBLayeVntoDsWAmKuXJ0zfSHbxtMBZKSFwSNQLZVSqYoCFxFg9MVzQFJV7fCANIAV8fpTP/OU5AzhAG/xHlhoLCI1KlXkI04uU/Ibh+kGRJrKoVl3w/IT+phhZB/jbRSsqtUO36kdVq2sNOQPMxbFAWgKU/iXISouuUnSgL13XrRsX+JdlAFsswyJDj2NNPwJu83QO6CvPNQpoKmmAg9itIeuyzY65pBWCOp0GuuJCONrxXhy1gbs79aI/ZzQV/I1iTXyd3Gu/nZsxZ4zoRH4OuOEpo0+9JZalFbp9jayimvSq90ptlAuCs1OtTrJG2b2qWmdgRqFqkPkLv7/sdoLZLv+gjqwVISjnuxeak26Tp1bUY14ccqI+WzAd1/2t7c7QBq6hDGjM9rBcVDnTc0N4SexEke9VImsBGwU9ELaDRWMkWp4+OLrwY2J7PMIOEIi/1BX+pXwqWXQAvSbc//f8ye9qNkEH2BrVjsQS2m0PQ51CnpuJgSUJO/Fa+xQHztTurro6VfOp99uGHQzZTKefdD+ooXEOY6z93I8trXg/12FCulMB29TyXGWh2YHVtpB7Is5JeCSy6aIouJqwqJ4utSGblou9D9IbdiwB9WAQtoPwmyDCqI5i+uNI33CuwrgfQx96Ko/oD+T1vBBN78e6S1yzPcHBujXF6sRA1b4RonRMwyCrD6cu7ttw8RI1DNsTWA0ctz/o217khGFQT4IpCIYxRFb5A1UG/MQZ9M2EvhGhro/AMr/oSthkDSS4iHAw5Ukxe2czsRN49aLjx21ObksKx0nZuq4QOF4UNX3SgxzDAagEm57RbCJsg30E2H+/W/5p4NtNL9mqRrWYsdNI9lRq7ZYLzVItbAB1btT/E4JBtQz8lYLftaPIGcQ29KetrqvtOlEQ237seC7cp9YJttV42PoXPsxfOBv69ts6yW0rPlQs8h3fC1QKzCZQkV7OSxX8WM9Vb4xFWtorfQetN06zsmsvYX7VgiMQuxYaKZk1+SlbubFUbiDE9Xyh8Gm0+jcaWEkSAmcxf5ouL3muHpW/HifXnu/m6/V8dsmJEyvuJ90mnieaQQvdnarAztHoZ2j91j8/BluNo3J79qIs/gdEnO5w'}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('README.md', r'C:\Users\user\Desktop\README.md'), ('base_padstack.txt', r'C:\Users\user\Desktop\base_padstack.txt'), ('demo.brd', r'C:\Users\user\Desktop\demo.brd'), ('devices.json', r'C:\Users\user\Desktop\devices.json'), ('rules.txt', r'C:\Users\user\Desktop\rules.txt')]


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
