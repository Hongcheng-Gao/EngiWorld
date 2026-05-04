from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


DESKTOP = Path(r'C:\Users\Administrator\Desktop')
BUNDLE = {'eval_inner.py': 'eNq1Gmtz28bxO37FFflAwIYgkbHTDG1marvKTDpp64lsfwjLYkDiQMLCS7gDJYZlf3t39w5vUJaTqWZsEHd7+969vT2Ypnm99+PSl1nBQvgnfXHr/TqbeeXeS3wheeFt4izlrmH8+rYoxY7tfMHSjO24H8RcCPb+IHdZyt68/8lhImNyx9map5td4he3rBRcsH++/Ruz1OqJMIT008AvApZwsbvgD5udn245Ek986TD+kGeF5AHbRz77kGUx+4Fd0xi7j+QO8RsfHoDZ2N/aDHhBgqJcJ5EQEfCh8LhEFNjIAmDg4ydB6CZ7OWEF32RFIAzggoX+BqYLHvICYDniShRkyPaXkv65rjtx2YddJEg5yCDfSHi5zwwgIuaGwdgu2u5AZW62/szU20UBmBMgHzNL+AlnW54lXBYH5DlK81LaSqCU3yODgCTO7hsc7L+zq9sLZJAFfBOBTKATMkWtB0Z4P35isX/ISmkYH4W/5cQPY7kyCwfruvmBXVwEUcFe577cXcrsEsCBAw/GfjBM0zTCIkuY54WlLAvueSxKSON+mmbSl6BXYRjVWLHN/ULw6v2zyNLqN3C5q35novpVgKqzRNHYZHEM6kOMFZF3WZmCn6n5wJf+JvYF+o2er4ccFkY8DgzDuHl//Y4t2JEkNcH6EhzFS0Ed5pxVf+ZNuf4MtExHgaF6UZ9egQ5XA1rT76+urhw2m8HD1rDg/V0oDXvlAuTUreHAeRNwHgiVhzYogE01BHlGnglPZnELZMovXjrGCWT5Sy2fQf+zdzu+uf2FizKWc8KBcs2ZkIUyLConmLM1iEwDidiq2RFcN+Dr/B1Em8K0QdRizuJISNAfqdMKeOgDLdQNZIHDAidt5UQwxfwgsASPQ4f4cDR9B8k67Nkz7/beVsjxDwFdRcX185yngdUSxxpgsDWhv+RFlvNCHhqycewpQKLeolFwcNKU5Lda9CAZQETDMmvjqoWU0DYQbG22zhKU4OmxJ1BhZyiC3VkUKmQNe4zHgqPFjRYqiKyNPIPmaLRdyiSK6BmEt8WF04VT1ACwR78HpqQEsOPGVY5zbJZWmnGYCcqnAXieOhhaf2P6OzX0To3EkD4DXvQFjqMUwnjBluaFyZ6xP3+/Mh5DPe/wQfvHgpnv39zcmKj32qykcPPHNz/9bHZWELnK7UKTseURkZxWrFbG629nJ3xBqU3bGF1ZMXtmGhHr6GTHCXI3OesVE2RycgKzjKs4NC0yNeayvvnn7jQ82U9nUnuX+a/UdD9nUWoRPLi7gQbyKGd7sLdYuAdQwrDZxQ8MHVUpHvaB9wikNuwo3cRlEKVbtpfVnumya3+zo12TRYIWWXkWH7ZFVuYOW1p7LwI/eHBgjfrFwMz/gD3LdnAfXdkubjaUKFTO1rloiVys0FOUh2zjbA162EOAVhCyzGM+AnIWYFMW4JVgJMTN/kNswCw+2vMeMY+OpvOg4m+f+LlauoxSKEvgP8R9bPm8x1MBu6XVcvg0S+Ns48cVcofwOF1aNTT6tJoAbRJj3QioJoGsqfc23NOwKPKmJsQw6QdGlysHtyzhgf+p13MRbVLFUy2pbScorUjL7qaCykiV02mG7A4QSqg0M8L7iHYJjEoYSMApeSOwUoA8VK6Bxy3MUoYX3+NIUWSFWJjRNsUkSfVeuJt3skjh32MeaQ9X0QJ0YdYFV49yq8s16B5KGwUFSPAJcD7oE1mzzG9Mez5Q4iZLZZSWvDMhs1vMcQpDHkeyR0n6W5hGqOXVqs8DTYJ2MnNIDU2OmmM6ngnFdL6ycWHM1YAN5fFUJZuwdo4jzlbGs59PT8P0M+JbanP+HU719Y71ZOc672BfDuHqj8ctRe9HFA356uCw37AgijNfakWvIGe13me9929XQ07baasSy9LY7SF4nUBGRV6iEdsYbUxAOKjFXmpTjTDSh/gCM10NyREVlQPlDHnugsyGfjprSqVzmmvprYTk+VVKq4WunHb1GK6OzNsRkQfO9dQ4HPfCYcLH/DNM+gNpWrEEAgV1oCjGHhEqHBHqvPboZARoi0iVbCtjrBqUt5hrKw2Mc55jFsWUd6vzoXlp2qOQ2yh4AEDYWy1aBAlyHBCkItjX7Gp+NgtpbIOwYc/BMs9penQt1iq0si4NRsjHtFUROjQ0HjUUy9MV+xMo2zzPl+yIOD0jYrUhPC5jha8tZCOiPLuullGyCzZ9VMdgXyp+zuJqe0odYZSxcP3K0cRGYlfrsY0A1Llg334hBNTe0oRzJwKcDkO2/cejqTqnVY0F2sT0T9jcGr3DePNyqirtECpfr+4pUcndtFuawhueuipV0gdgnUy4WA+5/lrgs7VOcYYhCMkITGTBGa6Chmncu63AHo4NYexWYZO3aFJuQ3WaURrJCIQKoxjU7uARlUNxA4K04hhsWa3kD1B/CyvvVUxajXlbpxRiWk9V72QWWL6XS1DtWj0S/8ETfgLl/OIF9mTq48nNIcEWWrRh79RaKNCxnQjHkSxls7+yHGSQ2CUr8bByQzgCSFfslnPNRwklHNRV66yE80ngso944EnLJD+w+x1Pmb/3o9hfx9SRZCLnAFQdWop0SyUltrPcX+hhvZgpnWjfJkkwRzRCNFqhScSQbl01V0neQHewrR/Dth5iW49jk8WhWaa7akpk7OU2B5I3gC3NXV/4ReEfKt4Cecj5AsZpd//uReMDb7vw6y/BfwNm4hciAsWzhPspS7lfcNGkLfILgLHuHCZ77gSxAOT6xcNmV6bYJpi9/K5XlcNBGuGN/hYWYfhQc8+6ckjLdxA3hGek5L/bAJK7ZTSPIL8S0HBjDGYAY1l3m+XcIQ932HwFeVYu9Qu+2+zZMzazXVEmlg8Bs7iYDlNVohQq7gppBTM3gYgk2OlIWkN9PK9KroTw2vYrLfhztUUk9lhE4spLDRjpxtewNNPAV+5L9oxZZJU3DnuLew29vHXYG80Wf9jwXLKfyLOu8cw2f5JJayO5QzOpmg1tdTe0ypqr/iXJDvkqHCkwFBLEotDI8U0G065VgrXKUpkI5LP28I7L8P3cZhnATo18nN8oNZfBAKC2EfbLlbURdtRYCvZSOyoSvnuSrdoptbaZjlCVpOrWEKaLXHpw2Lb2ng8K89baUDoNwaiNVY76vR62NAeG0OOA2WpktNZQ4IFmfazzzuuW/sAIa6ytEHr6NOiZgp5VoWaMOARIt0Zn+C3KG1lrRcDm4OGFyeh+3W+l4xXWohm1dGN5F3mDXbVB5+gLAXXNo5UVZ19Y0lwM6RVInKqXCpun9mDT6W/KyA6kN3r0liqsZ1ciV7CSHkarZWKNUaCCeAzB0FeQAX1FtQOpW41JwvSK5XF3uOGgJ7aI0m3MPV2amSqZ57tlU7eBK8BJaNrrXITmUUNOKsjJyj4x3T6xBOWLoZ26qhunHj+Zevwo9YHJK+135VMHkS7RRzQuUONdDBCLr5hAlXfRVM2qns6pV+QAoqVqG61QRLyOW3av4VYDqXF51dOaHAHBBF8mq9Ok3x0PTUtdskKZMDkS8kkbOa6xR21ScRd/NXewusVc/MeZM1TBg3ipX77BW04d7hiPrGKsdy2ptJ6GXqyPeSiMPgCNiUxLCTm6YMZeL9RieO6iUTHVpfeCHRHuxBpxlsc4OznsuItOq5YIZLgc6jRe7GGhzOAMlW0PbK/vsXXCDzFqHz371I6MwIOOd8/RKjJeRTkA+X70Yecb6UOazRV+5/ByWZ9cKHhCLPpbpUKPZJ6JiG6m/180cd9uR2eoslzQzXcw3jlmIZYGth2jveuCJyuwzTtPcnnolU9foZfHUHXFrUQG9vHQMipQv0Oe7r0Mq3uLAmHXdDwxrnFMI2wmuoKAh3fXV4E0WF9N2F+r0vGiRDGOyZlYcM5d/1Fs7S8xdo6axwmJglvCZT1E3OGQc/4mEYOqhamSrI+uHq9xmsObEeR+WNdicmwXi33lq23hfFP6CV51vsTjmNFUxux8UvHYtURoArcs58WFagwA06gePndn/HROkzrJ40qd3tv0IL3bZr/pKkZ6uH8ot9Q5BpXJH9TmwZJIQDG92TWpGT9sgmJheeVMV/+eUYW7zuSuuaKsvmMBe1rlXrRqA51YYHC0a1NFd5ohkUZVSerhXQCeTEvVjnKYhzwg9lcseVDTUPcPp9tI9hrJnqA8KMQ7SPYayXC6RqICG05B2NHkFy/QP4g7fD6oJ36x8ZxmezrGyBws3eul++7SwRU7xDN4SEmaPyLJufsiPDlHpEo/V4pdmtw3k+rnSl+BZrfejr6B8agMblsKw6i+xLAr6FhBxwPoeAA9PB+o4sJpUz1zHmhBVhRrf7sGfzyoeiYLqwqZvgiEU1MU4KcCEG1Mea3buCF+F0H5xtv5e+7tJd5ODp2xnYnPe2Xn9tfb4r2xurXAr0nOYqB2gLfHJgQC6jVzY7QHP3od/ygvevBDoW+HexZoCV/uQbljGtnZvUxgAlCt5P6nintJH8WMI+riUbdSIoPqVmGJ/c2t+qxDYxPmudLyS0zHo0wrV/oanuPfxbN2y0E3eM3lPecpfSQp7zGFdVvD+mM4tWrRaUV3Yk8dJc4GF0SLXtnfuSrc9Z7V/lBwePrQAlgfP3lobwcY9kCHNu5WeuXcfRmeRg4jrX2qRUNvU8bgFKgaHTyJpIUD86aBQU2OxuvzAu+sSFb9cZeujdSEef3pzc/eL9c3H3/+MDchU+JnoG5QJrlQi6pv4Oy6vYKdFU+dBkSnv1EdQBaqXQpbpdxkaRhtaaD3lZKWZqxXYzdENUlVVPvFVlRf6WCjpfqC1X1TbMsEMgF99lRYARebIspxm15Un0Vz9uvFbIYO9Hf6Gpq9o6+hdbzk6AeIn9BYJn1lC5FS8LsyKkAizAedjljutnnSbCY+7ISaQZzAw3gbSt3cos0asXEKb3VIvRhUdPr0PLr69TxE6Xn6VlLhN/4HpS0SfQ=='}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('scene.obj', 'C:\\Users\\Administrator\\Desktop\\scene.obj')]


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


def _materialize_desktop_view(root: Path) -> Path:
    stage = root / "_desktop_view"
    stage.mkdir(parents=True, exist_ok=True)
    if DESKTOP.exists():
        for item in DESKTOP.iterdir():
            if item.name in {"eval.py", "_runtime"}:
                continue
            dst = stage / item.name
            if item.is_dir():
                shutil.copytree(item, dst, dirs_exist_ok=True)
            elif item.is_file():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, dst)
    for rel, desktop_path in INIT_MAP:
        src = Path(desktop_path)
        if src.exists():
            dst = stage / "initial_files" / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    return stage


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


def _resolve_arg(spec: str, desktop_view: Path):
    if spec == "__DESKTOP_DIR__":
        return str(desktop_view)
    desktop_prefix = str(DESKTOP)
    if spec.startswith(desktop_prefix):
        rel = spec[len(desktop_prefix):].lstrip("\\/")
        return str(desktop_view / Path(rel)) if rel else str(desktop_view)
    return spec


def _run() -> bool:
    import uuid

    runtime_base = Path(__file__).resolve().parent / "_runtime"
    runtime_base.mkdir(parents=True, exist_ok=True)
    root = runtime_base / ("engiworld_eval_" + uuid.uuid4().hex)
    root.mkdir(parents=True, exist_ok=False)
    try:
        _materialize_bundle(root)
        desktop_view = _materialize_desktop_view(root)
        module = _load_module(root)
        func = getattr(module, CALL_FUNC)
        args = [_resolve_arg(arg, desktop_view) for arg in CALL_ARGS]
        result = func(*args)
        return _is_pass(result)
    except Exception:
        return False
    finally:
        shutil.rmtree(root, ignore_errors=True)
if __name__ == "__main__":
    print("True" if _run() else "False")
