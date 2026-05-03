from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


DESKTOP = Path(r'C:\Users\Administrator\Desktop')
BUNDLE = {'eval_inner.py': 'eNqtWuly3EaS/t9PUQtHLAENGuLh8c62TcdwJFnDGFlSiIdJ0wwEGqhuYogG2iigyZ4mH2AfZB9gX2EfZZ9kv8yqwtGHpD0cYbFRVXlUXpWZVY7jvFlEWR1VRSkm+P/sb8PL4cG3Yih+KYpETMsozUWUpdNcJqIqRHUnRVbkUxE9pkoUExGJRKr7YDB4dSfjeyXcKMvErFaVmEdKeaPB4CAQRV3N6ypIIikk4ColojzBglJJ/FQCLKSJePXh3buT1yfB4DAQ56BTReNMVsV8T4FsKaVQRVmBjXFR50maT4fj4lEk6UzmKi1yICqlOAi+88V+8Cf6Z/9IzAZCiIe0usMuDvfFbCZkFN8Fg6NAnIgH7PBFMMdmKvlY1YBOZ9EU/ypRyoksZR6DGiB/yNJxGZXLkOfVj8w9JEHIOysnaSbxrYpsgW0VOXhT98JVMpsM4yKvIEriHsxn0gsG3+pddhBYNuZRdUdcYKUsIWGMvxSqHidpKWNoahkM/ogNVCKTEQRd5AAp01lapQsp7iDP8zdXrz58+PQazEPuLACRF/mwKtNFGmXi4lIkURUFg+8C8ZZVXJSpBIcVBDki1knPLU5GAKC4KMpE+TwL00gIhozAyOKy2QEvTPOokjAeMpeHoswScUW7UjCmdJLGUV5lS5FF5RSbrO6iXC9ljfHq60C8+b1OYRySlvrAz1bn7gfBgdDCAL+e5dcQhyKimPlhu1Wa+8ZwXZiImHmGBiHUeojJfom/BvFwHCmZMCLSd5HJEjyTF8AM8rSqExkMHMcZTMpiJsJwUhP5MIQZzWGpgMoLLVI1GNixcspmb79nULX9XSj7Sy2VRkpaijM4EgzKzDVDPgxOZslggNUBmUyQ5kqWlUsci30f+PTw34s0d+0HdpdHM9l8R2NFf12wD/MNQ8/zhRMEjuc1POf1bL4kN83ndigusixKosFg8I148ziHvMh8jb92fdKdyQouAXN//ebsb+E7cUwuKvR/32iNyGQq9fQZpuG8zbS6I2Lt/DnPw6/NPPw6vs+lgnxfn/4cnn94pxccmnnt8mOKE0Z9MAywfN6LYhytkmKm7ZUM5bK17vGSqCiyKRsjjfWnOTCxic2kNosxGT42Dq+FOGJ4ZwkLj4uSDCoQT8nly+TxSbzUv5ZP4sdjjmzYZpYEg7efTk7fh59Ozk8/hD+fvsdWjoJ9iPjPjcoH/K/gUDtiNZMuR0JVJX9RyJXJCBGyyHhgpqZ6dguWMzAmX0VlojGx/auRyBCfQZpty03kJKqzKtS7Xx7TJAyD1mNKREnC4c1nPnxD3yeyvnjxIvQ0avqPlgWaRhDN5zJPXN6GuwHpGQJ/npfFHPa8bMllWagXMtUO9lLC9XLet9uh5LHnAsyNAw3ICowpqHeX7SJYwX+zUJGgdlA8CPZFOtHIWvaEzJQkQ2xFhRAPs1jHkuFIUJD2jTN0xAvxL3+6baa2MdoCNsBWmBNHiJvV3seTs7M94qjZMLOy99PJ6bu951shnB6K3n8TZxUHbFA/HB0+C3xAG8+ON9hK0HK8Y5r4+SQVjGckOmxtFZThbidzE8dlHUBQK0bQ0csoOJg8ex0mjWKc33JHRz5mCyoekBpCilzwxpDDfzgvVMoBGnFK3RnFIKR/0kjc9/6ROSmGCJMxzkQLIKK4LOBFlO7QQYlQlyM9QohR0NxMMSbIIkuxyyFO7wmOPI4oKkUUQkqEkz1XD7LktKimCE+BBcEjr9Jq6QV0srBTV2wh2jLIKqZkFcRvMJUFxddUdiyDVhBDtGgaNGf4mu0sCGc+DyIVlWW0dGldsIDxy0dfJNVyLo8xO8mKqPruW68HmiaPu4HDFGb+6AEyqiqZu2ugE4YOVPoPOdrQNTZqrWehbmjhrQYHGE5Smt/wP3DxDwlFuC4OvCNPr2/nEI5jBHUK7C7AfQ74x/sb1lAvyBRglGm5wxQ4LCLVcXmdLPVGtYX4guC7Y4eeJ6p6nkmQRHqm9SjLTkqFhAfHKOQH5bX5Gmdl4i8FEhYWrU5qbf491pFJU0GCBYQ6+WrxUq5cplE+RSqKuC+jWWNHSML//+2oUqGShHcqkepUJdsCMgiYgk4WZeX44j1k0LeEKv08nBblLmhjEIY4GOUvRrlpVpR6p3ktexP1om/CGtXN/u2XrL9K1wBTA7jL5hfp/9JZ/i8uOsEG2cvEMRIiklCV9r8Xne+vlBklV0iSXIPKtzj6tOEfWAcHXqQ3o3e3t2tiJ7nXi5tqyyQM1Po/eRl51aLv0VhhPZcTsLDJ1UM+IC1Y671vYbI5ud6w468m9+/EcmQJ7LVtkcP2HzWlhPZXqgyLenqHrI4CydA6JlzkSvyzuPYBPEPFhYoJmeldp8ZgL724ZFSmjClrokxpaKDTBB1pFJXUadwx5FVPSk5ymVw5I8GK9/nzuvlcW3nRX3mxcyVxERJXIZ3/WORcOeJJONfO2sJFyByHDYCjs821ZUgcMHFXz6J8iCCUUGVA8QhVe7vyWW/7go4+rmSH6vca8Q5JKNfQrAI38sd+7JGIL2E60YtH8QcxfrHEvzHrTSEwZZRoN3HtQhd0NoVX4il68sXT+IlaFXGZIk2/Kx6AbhFx9KXAzGUKEWGVMSo+8APxC2lSLnSsvSLXuaa65IH0ZIpXNac9EjTHYiQdIKp1zpiaUiOwZsl/H7Ef2ODNyBf72hOW7ciBHqm1u7RLFs0AVgx0mXPKOcNkaayueij4pLryySJ/9WgnCPQFDrChLpRtoUbWTYwevg7slnOleQhm0aNrTkuA8Qh8356fmvAvdDY90DEluQjsY0dFhOyHneNauA09sKayaOwF4nQifgX5gS3m5JpAuSkAUBlMA+OLjO1XzzcFP7Y0lhmU+VDURm2oGqsUSRkUeY/TJZdlGiNJW/piXFe6lqsidS/mGdBpv2wQX2sxIPUII5//jE0MLqfUfHKHLCHvZnR4q3mGqJlnMl6ScvQoVVOYkShX++xMUNeI3Ukc4u+vzrPOD8njIiJBq29gNy7T9m774fibdSIpoX734f3bFs14A814E42SiOzJ0GDjwWNx9tcPn86tLf2lTrNE66LrktSSqOSM/esSTgnHu0B1NUUQVkbtJAoYOvAaVDb6SWP3J1qWyLnqWR4qVKP37o0xd942Dt/O5xifWI7DX7kZTkdMed6tNb2zJkLosGBESbHBiAMBQtONCzmZqHCBkjTULKAkiLJpkKlK/e6e4CDzRUmCOW5TDQNU7waq+0C60rtMYDj4d+wLArOk9eQFT16sTdZW9CeZKnDSDVGG/p2cCWdwob2YXFjG3DRjS4atxhEKJ7PpVOV7lbgKtPIMNnhkhoqjIm6umKdrrTcFI9FxkjpnOMrSSesFOgLAXyc1KH1vcCEfleVDqrhOEa4m6xu786g1RAiURLiv0lgfJ+Klbt84gZXMFfZMAiKC1vKP+aThKpCk1kyNe1NUSRsk19uRXO9Gcr2O5EJzcrGbk4svc3KhObnYzcnFZzkxkr1s240b7Ury724KkU4mG53XS4Mnas4YsGF7Waq/vLNmrJUypdgTjZVLEtV2Px23Q+Om/MLoD+JADv+1U4BRZ5MaRZROuE6aTxyPl0biR6SYPWnRxyYkVr4EZn2sdfIKTOklPx6LtZ7YoJsNtnlRLycizq+8tcyIBq89f7A1N3Lpw1vLkGiwD3GZMHtdlJGhE2pT78yMu6C8HZ0zFcgk1lbzbHd5N7myvuYwTG903AHZlZe53QlD49nk0HIRZaG+mlGu/ksJtUmeVUxHg+0Rup612INA/EQXHfoiRztDRK2Zfru5QQfW2+sfp1fQWwiNysV8t2EYB9RedLgtrVfg9Pwpgin5YtLByagmdCckkKKvMPK82Q5S8WA30vOyZpwaycqyRe1/7pUTY4TTSOAwEB/56koXBuWyZZqqaY7s3B4PXum/jEA7wmMs55V4w3/Y55E6be4Z60N9O9bdMo8IWZZFORIr+U/lF/fZMd4uRt7voNP2o+N1rRHgPQvzsaT+patg6e06fRGGNfwDk6ZOaGR0RF0MfU0nqP1OfQqTF/KKj5DS53tx1lA+BuoumktU2AhBR5uyuotUC9qIa7DRQqyKQkzkg9AVdKf4c1ctiW2dRCPSWe6LGaXsH7uJsE+fbaZslFxx2XFsLixdF3BDIPCCqqA+kguwkkoKJY9JFxbM3KM0cDf6zsQX+nLE/D2/3QZd3MPZZhS7s8yl+G24uElvQdvixpcnfjgW9raE0oCU0okyQubm2gbahvlY3YXt1U6nMtS0uxZlbmpbSawsO/u3o+Bo8uy3Iwd2xOmapJ091LNi9n0roJX99Szc//yPldnM84YRfhugpt64XWWT1dY1m4bk6Wv9Vd3z6th5a3R0vpmGFberCNp2qPpdlAa3bWmkM44qWsB09RyWiMHHDNuQnhPlBrTFOM+oKgtQ6ciy0yYCOw6hcggMa/hWPQtATlEW4Tp0u+2scdahPe9NjFF03e/Qv5advgAP2yvrjhE0aJGpUESmfXVNon+HLqzcV81un78XuYSeovZivq9Q7HYbkXZ3eVGSB9hFQSm5yHOd336DkpyXHd/mq/WQAsExgwUoR8rKSI3u25HMQB/OS/5N4qVV68Gn3/SwQmpw0/G31kBp5vrDE2dvZdl+3hOrvVTxdUnLpr4owbbffzjfezZPA5i5FlM3dHEHJekcy8Q/3/TuPKctA16Lx7zWaLGkio5O1+L3vk4ifNwW1K5T92sC0RTWpdHwz08hYCV24Bmy+enDxfvXLB7DnpbNz6dnZ6fv3+49b5VIs3qtf909vRv6dPX+8fSdvXI/bSJGz48oT+epoICHtzKhQz2djbbeZT34gvaDYECd061LEE3hE1jkPlAGfHTIbn2nf3sbINsEv8Nvc1SU+gWI43+G9Pa5ifMR5YjuGYvVw/Pj6g4eW8rfaxQw4r/+7d/B3ePR4RbM3prCP5sCrR/vu3ew46Rv+Y2pJ6QTTeinif/YRps+mZPij8H6m5k51IkDyFyrp6XqJiyb10W9eyoa3p6odK43QGTnHpy8+IoXPeYVz9cngVs52JoM8haQ3jVMIMXj26olqH7fP6lVPXPnONfbPK05ySwacKqiGV2H6Sv19YO6eYbUFMMj2yX/UlGs3/7YFmLnxZh9DGT7jkja0/je9OGHYxlRM3r9jVOLyrbIrq5tN9Jda25qtJ6upMeSX000hzl9h9ysOxbDA1MGs1z0DUUjnY6d/I+ar6YLRhTMHSA14PiRl30U02m9cah7KNrUkontSkepvdmyBSCAkl7/wD8ObrtBVaHabzbbd+OuDNTGDAU4e10zMBdHvr6XG9seYppPiOcvXPbYly6EsZtwNA98KMsAppu9pjreu0W+qV8XNZNtgY3Zvo3zex0uoZ9oPaXXGsb2BPZuvS1JrAZjvFvgeNwC9unZDonhbGv7YA+J8SES4y6cywkUxeLVWuPEPJMYtPHYhiUt283+gc/Sv9nSWbjVz3R6vRiEHN1UmAGbazLOaE71iHnxFpyU05peSnHtbLPYaE5chJGZc53hkJMmYV4edTqy1IMnfPOA8RGMcpvAS1/0uK01wUQT59EtXSj71O6urtJsfbSSszklLa3zzGgvdjiY3Sf0u5OKT6uNFsjXv7jb/SZHQD9UR4dVWaPU6ORbzHcQF/NlP6Ob0lVf+7LE2YG9B4PdrbVpeolTm/xhL1uoIdYCou/8HMTuZUIn5BZaDOLrlCws7juFbPf9wYTCJKApSn096S+Lh6B8Mfms4LeKyAJ6PSvDXNsy63XVTIKMUwa2DY8zr8DsrXZELfUzvll585hWrn5LFm88kDqgByuYCvl6Ngy5mxyG5Gth6Ojda8cb/Ddt3ahy'}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('tex\\wood.png', 'C:\\Users\\Administrator\\Desktop\\tex\\wood.png')]


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
    finally:
        shutil.rmtree(root, ignore_errors=True)
if __name__ == "__main__":
    print("true" if _run() else "false")
