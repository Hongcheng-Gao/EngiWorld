from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


DESKTOP = Path(r'C:\Users\Administrator\Desktop')
BUNDLE = {'eval_inner.py': 'eNqlGmuP28bxO3/FlkFxpM2jT+c+DNky4jgXNEXaGrHdD1EFgiKXEnMUyXBJnXSK/ntnZnfJ5UNnFxVwJ2l3dt7PpWzbvtuHWRPWRcUS+KtDcR/8cvMqSNI1r3ZcbINtmFa+Zf3yXdWILduGguUF2/IwzrgQ7MOx3hY5e/fhR4+JgtVbztY8j7a7sLpnjeCC/eu7vzNHnr4STNRhHodVbCHua36ItmG+4Uh7F9Ye44eyqGoes30ask9FkbG37I7WXAaUEb1o1rtUiBSoylO+dRdGW/axWdOBNY8KQM6KnBPtq+KKrbMiun/NfkCh/gGEGYkH3KQ1S3NEm1aseMgtjSQPd8DEFR0QVyD+ZxFu+NyyGLxKKTMHzfnlkV1fF+tf2ZsyrLcv6uJF0dRlU/uw9taybdtKqmLHgiBp6qbiQcDSHYrDwjwv6rAGMYRl6bVqU4aV4Pr7r6LI9WcQdKs/F0JijYos4xHh0GjfF01e88pjMU/CJqvjNKolcBzWYZSFAm2igNslDxTCs9iyrI8f7t6zBTuRoDbougZ1BKgOYc9Z+1rafwMPsD1mSxXZK0+eQMcgcBOaduQBCSXVPwGn0fXhkjDiQVYYoLM/39zcTABtUwPo5c0I6BiE62IPcMgMQd74LxXILs0DcJ0SHCevTWlvOzTtfoDQSFIB3nrWGdT3batSi/6z91se3f/MBZhiTihQ5jmEQSVdCe0Rz9katEwLO7GRuxO4PkZFxd9D8EhMEaIWc5alogaTkQUdZXZkDWL6uMBNV7otbLEwjh3Bs8QjPjxF30OyHnv2LLh/cCVyfCGgL6n4YVnyPHYMcZwRBlcR+rasipJX9bEjm2WBBCTqBo2KQ1jkJL9j0INoz2M85kS+PEjpKcJoNcEuEawhtrJAoMIuUJz5NyxNJLKOPcYzwcEnbiwDVYBBdAHNyeq5L1FEjyC8BhdeH05SA8AB/QGYlBLATpEvHefUHdWagSAE5dMCvJ8tNv2a0t+5o3fuJK7A0rwaCpylOWSOBYT+tc2esb++WllPoZ73+KBysGD2h3cfP9qo99aspHD7h3c//mT3ThA57XaJDSnnhEjOK9Yq483L2zN+Qalt15o8qZm9sI2IVXSy0xVyd3XRK66QyaszmGVaxYntkKkxfQ7NP/dnydn9eiaVd9n/yW3/1yLNHYIHd7fQQAFViQBKjINVhxKGy67fMnRUqXiVuVV6WOLGCo0njbbJijWwtoeY0RB1U2bcAImaCvwA1IJH2e/sn1hPF/Rm7gebqmhKNK3KPFI5+11YyqPLNIe6Dv8Q98nwsoDnAiqiY7hYXuRQqMNMI/cIj9en1UKjF8kNlgpirO9zehPI2qrS2Kq+BzMsXSQ+rC5X8EXn8uXKuxRBdllkR+JBUOTWjtuPNq10bVfFgdsDQpGkKiaYnVAngT2k9ZZBjsvJ4MBuBQJAn1XEab5Z2E2dXL/ClaoqKrGw002OeYh6pmQ77wVqFT5gqJrL2iGBLuz64E1p6fS5BmVDvyKhAAm+A1wICkTWHPsb252P9BYVeZ3mDe9t1MU9phGJoczSekCpDjewjVDLm9WQB9oE7UAvMKKGNkbNMRUyhGI2X7l4MONywYWGcibjOWm94YS72nju89l5HOETziTr3//sRV/lSV/tTZc96stBql88MzS7n9DswWNHjz1ik5EVYa00u3I98/vt4PvL1ZhTM+9osRyF3R2DtyliUuQlWs3E6GKKwUUl9lLZZoKRIcQXmOlpaDOhoZGiv9YJpy0yTm8YfOMUNxLH8CuQKW6dRjL2hFDJhFCX1U+9NqmuKxjDXqO+p9FKyT/NdxofAsg2GO/3KhnYL2x3GPit+wA8wEIxcdRJdxptIkHfsJv5xTBUyEZOxJ6DbZ7T9pPIQTiqchcJdErS3kVei4cnPFK5R3cInGTBXn7B3jLfdO7bM7dnsOC6/7/j6JZXj4WUu9THs25NUhHswjxNChhGiDtqTLC/l6LweENtpBpUlXOhwwQwguwF1SY8Z7QFykx74fYqWYqwFd4fOPmg+oQeW8OpvVimK8S6dFK0q8v+yPK+bxE/SwfGOQcPQQ7bhQf5EfLJ8wWbWcM5hY4YEwoG0G3XBNO2j9cqXDhu27Ot18XBkbaQvB4oePbg7HR2Tx6F+6vX7Kj2ZhN7j2rvdrRnckoSHQTKAx+O+sMjeIIHmyCj3IQPR/0BNzW7ULtzHtU8NmZiJ5fOJB1LEEY5BC9mSijbtj/naZFfJymoB6H54brFxTpcrzWjEToCKxJjjzDV27Bm23DPGbxnPIQhtyUn6UNyaaItNEB4gbPz8bJFztSqUmNf6yj/aKOg7T+RQedg+M3DNs24Or08rNgfFuzQ96pub6E/t0t9rzp0EIfVsKs/dEw0qCvpbcZoCd+rNY30wGKIZRU/rF2z9a1CZLBaT3JYhchitba+HFyDQFJxNggnyeZUNCn4lVIs2lDexJBZJ0YA417KSXU38ySHVVHUWhl7bAo7PQzILRF0HLSi2TkzGZ853fcNjrWxSjUXQCDxtq7WBgTSDyqecNBwJIcv+Av6AxgWs9+NQh0D44XwEciP0wpbRkd/D9cC31ssbqcL6CGATQdG++Hh2PUuIuxgTPuVBgvUkmBhsNM8rVOoeQn4vMBhSEQcGnLgxe65mT7JDxBMwikHjqE0XJrqphFRKa1q8gDvSSdUNbzNgk/AabvqKI9Sg8eAj1ZnHTuIgCqXjZsSDgT7IYQ2CyLIzgu6DoZkctKnzVsDnY3wbvoJdJ+qhrAhqkUfk04+eGGwMGf0llk9mQuZHQBw2dXSlTWgqy9fyUeBtBpSoPJgvRnMF4l9avfP+i7cAViHH0qZe29dzeT6GKhh6SSWcpxZgWHI9SgCEY2cJvCiFODUCX8DowpeES+Ni14Vj+pKfQrWvO5V0GMx5R2zJykaHS/VWYXcWB7JT+dJJHqC4Gg27vkRy/B5eG2T2J1q9Bli96rH0dXKbS9uwBc1d8QZPjRpGet356Y70eI3DC/AIZPKJx4x5ro2m/gqfhJ0nCcSTcsGgo5odjol47Sk2igYt4B2S4f1MsKLNh2QwhNwwVgpAccWU84kmPJ5WO/lEcTSwZpuP7i0+ZIMJssYhOqBlPJ4YUR0n1HNrHLoaV6Gg4cAD5Dxh55FxVHj6IZLDEfcGayC2z51BdDHpfr4AS692u/dH4pK1EG8B47wonowRBgszyfnMucwgxkX/h5n2AkebuEb/D3euhj5j2k5FvHJu4wnXn2NTI8yaAx8tuWL36oa5u8Zu2YH4OXZM+ipnzPniAtHY+ERFx7VwsX5L4YRWyvq8ohmqDL+SjecxmU6CuarFvEbNuPXf/Iu3RjLIzAx1dF2cTKwnKkjp641iHlWh4tTK47/l6StN9/Ih5qyI1a9tG7mZFbJEzU+yVTVedUgD5uP0VTJ6XPdy+X6kdyKvVkgCfg/3t+mI9+BOpUnZ9W/dwl4eZKpt4/9agVqGKXtCdBtCqArd6QUfqhhLIZ26gG7C3r0R8+Q0ahSO4EsOIAB8xfNaH2v1VBAzgTSyuyBEaYjWBPbf4UWRjhdHtstiUvvjEwguQ6acmiBDsdbk9bzvup7zzjH+lcVS/NyapHO/ZfJWdXfdrcjo7ZH5iDv7CGC+Bwcm6i9Ff+tSSuOcdo3qMk+WNUw6vfQg6V5VLOpeRK9XlpdGjaK0FaTU6wZDNp+HhuExxdzXjf7Su1PPRq+FGTGY+YBHWD7rQ6lwQPpiVCKorOpAgeOKmVOcAPKVHHHw2jrvh4bpbNJi6fPA6DQ5ug1OLLZ57u0dnBh3rXx1Op3bUpZ4eUd6UM9ZVTFTW7Yd/9+91Pw893Hzz99mtvg2PgLCD9udqWQh/TDWLe9qMDpIpC/uRD9KYN+TULGX1DDyMpC1OAQSbqhhcETMyXQeGRxO6qKpmxzwmoj9NMrHLL0rzf8d9Wm2YG6PuC3yom5iKq0xJ9pLPTPbTj75frmlfGDFPqVjWpeSvQVRE9YHJt+YAINkDbPAoeQ3pVc6ZssKS53IQx7ij/c0EOHhpJXvGizTmbcwq6P1AtlNKAmOAjojjgIEGUQqKtiid/6LyPWfvc='}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['C:\\Users\\Administrator\\Desktop\\output.obj']
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
