from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


DESKTOP = Path('/home/user/Desktop')
BUNDLE = {'eval_inner.py': 'eNqtGl1v3LjxfX8FS6CIFGt1WRcoesYphyB12uDukiJJ04f1HkFLIy8bLSmQlL1bn/97MSQlUdp1LknrF4vkfHE4M5wZLqX08pY3HbdKk1ppslV2ae54S355+/7V5QdieA1L1YLmVsibJdfACcha6RJ2IG1OKV3UWu0IY3VnOw2MEbFrlbaES6kst0JJs1iEuVK1h+Hb3PafO263/bcy/ZeG/ssczGJhDiZvud3mQhrQNnmWERVm/q2ETPpBJbTkO0gYq0UDjKUZoXlO09QLasot7Hgv5MstlJ/egekamxFUhf9eLD68eP8Te/1XUhD6SZS8Wp6f08XfL99dkoI8ymnx7vIfb999YC/f/vzPX968JwVZLwghhJoSJNdC0YzQj5Vhd0obi4PX1fjdKiEtE9KICtj7ty9wbsf1jZCsLS3NAqnu5gaMhYq9ZKaBOyZf0WyxWXx4+9PlG+bk05CXateKBhL9hCY/Xlxd5b+tf6VXV5v0Kf1tnaSb39a/Xpkk3Zw9SReLRQU1YS3XBpiBfZtY2Nv0wvEzlpefcCMbN9RKWVKQN0qCG6PNWPUJJBGS9CLktZAVb5qYDv6JOsAWBaEJHRfwT6oKRj4RipNgCjsItl6uNjlvW5BVggTSxRHI6WVoJsKkM2FETaSyj7HWXBggH3nTwaXWSie0k9e84bKEipSNMkLekJZrkHYLRhiantqpl65VbZJ+BW9R+zMQxkHhQRwDnRZy1zVWtA0Qq9plA7fQENi3GoxBH50JGR02yhspzsD/piuvddVZtPNIAnqkBgeZG8u1NXfCbpMn9El6zCIcI7k+WDCJG61XF8vVJiO0s/XyLzTNKyhVBXhQAj8YmJK3QE/YS2xSjpaH6Q2RKD0cwFT5n7UKpQnsWnsgZnm0Yw2209JR7X0RHYihB6HuM7IFXoWNB20LI6SxSDuANMLEruZpjhgVEC4r97F+tkGbR5oj/EFAU40njW5dbkVToVvj7MSJI+YO6Ij7SNHfDcN2ArjbzxB3NN4v9pCYw+5aNRnBmBqIoRy4jmKMVHpA2qPSaZBpQCa4lJLnBfmT2zgO1yu3cSQ/FTUcAMLEB+KCXBDSszTs+sA01KABN2819IJqd22Qgtw/DIJ7nKnoiJIR6pfo5MACVVKcUAl91y9HJouhYMDCTeK+hxm/+flGUcrcgK2g5l1jE2P1iLI+36QZWW/S3v49+6mVhvvRq0UqveON+A+E+PoNNjoa3aDDcAd8kxE6RXis4QstXkhyP9EF7TpR4RVrjeW7Fr9uQGKio/RkwG5BO28d0B+mWi2VtEJ2sJipOSgxVpITJ/2MQhvFK2ZaKJOgKIx7RLUw5jcu2cFMJCNUSGFd8oESb5XF1M2h56W5pWlGJNw1QkJBaUq4IcZq4LvoCNSdIYXTXFKa2/yvorTvgFegEw86lfVeq7s1bbnmO7Cg6eaCuBlMIYFu3IlpdYfKRsoP010p/g2b2ilTg0Xk//eW1J3JjdI2+QSHouG764rj5AUR0iZ+W6At7JmQFezpZqqKdVI3igdATOk+UnSeaPJ1xV4g1lwrmyHwhXyPtao5JO0+I+0hIzi4UbJ3JZcNkoK84o3xFtZquBWqc5vEQBfgyZKsRrfpNGYfGUn2bPg+9J8pigKy26GBQzLliH971jNBrIhhAF33U5vYI5Nk4ECek/aQkj8UJInw3eTR9e3C8578gLIOoEuyH6V9SpL2QJbRBo6IfDdhFIOSs4jULHPpleuilRsM69GmA3J8+gG4vxwUZ1a1jNvktjLzIyy5rETFLZhpaHNmhSe0yshh9ftncp6Rw3l0BokjQM7IKiV/nJjC5FR2QjoW+3NnIrD8nvxQkNvK4L8d3w+LZ27xKLfj1ybZn+OBrFJEWcFydX6chI27zGFvMe4lB9zYeTo9rOP8cYYdouZhRc5IckDGqJynBFUbpPiODBJNfBJ3M1JKUfpI+cg5+CeVHJMvf3zgC2BINGBJyDAeXWBYybBWHIcpWT6PSsTZvT8uJJabT0xURSghM2IstC6gFRGLNL4q+zAIe2GsiSVJMXU8AdKLNrlP3bUDmHxi3drfB54ahk/iK3w327Wolip31S0z5RYz2p0wWLzQ+R0dLimXbevDyHIM5JHIcYjOCMhSVULeFH0ufipoe1YYpNHfTkbtKWwU5D1eOruSm24njauFcTWvMRvFzM+gDqIiEy9LTLmii3dcU3xcwtvrxL77c/iKjarOtp1lmAq6ZG+suz10jjIn6SluX5oDjKeKN+YXS4akBG++UDTYl9Bacun+CSWRKuzLRw2ypkK2nSWOKnGzF+Qe9uXDY/YW2PDSMrPlLco0nGxBZs2WIQNWdybF9VXkoXmJjZ4hukRtn2TgjeZR0GDIEVeakZYbA1URTWZjRbxvobRQFfc0CEcvZrJlhKJU9IKsHkZEXtqONxO08DXCDxsKeOkkbODKxWd8FbOOwkGtn22OvfeWCaybfUxE21/Tj0xIuolqDKk7s50B+ckYzAUlIW+YrGewoUnVA8RIXtNQsdsBR6u7/AZsMm2SuWh9Ak8c48X9tBmab6Udo8QttiOksdsW7WxAPdmLm9AIPpL8BAfXFMjIh0ML4XPsFaS/7zsuNRAlcZHsy73na83faY+V3ADbcVtuwbioSEezDb6QYGIQHeHSmZNLEZ7l584bJxCCLIM19TAnM8FrpRpflQ5KjnqnNE1zY7Vok9RXejvXEDY1Ri5I/FGm6QnnrKlUMrRgAsGMfKxMcY9iP5x9t3yWn3/MyOuquPdihrkXGfHUgwHREw48iOjqoZnYqe/54tqgLdf5jWdEdqSN2DAvAvMxCkTVAes36UL2pKjAvWVB7RneZ2mMh+1Z14iMtH2qCR1pPW/UHehkQuaWNwJ5x1Sx3KZWd+5SqrF2oQ8xTr/xGRr2Yh3WN9nuRHZMykulNQyt88h4J5KjHR2JVcyVe8KmUHEzqDTrreJxjabTQ7RbDWarGnd8cSnhzm44M1PyBg2lD8jh4+kk9n43DVjYtIzHz8mzSRosZB36SQFMKMkUtvuTKV4x4RLKCGzCzAwQ+iL16G8mR0wO9T/d3Q+RUnxZkn6TQYxMS97yUrh2EROGma6uRSlA2vFyn6jgxGknNX2OAXcQ/EG+imQng+z3g/AX+Z9vHl7QExrpW2Qn9Edq+ryYM6LpqbAz6vQVvZioGHuMsUrZCwSIZ2ahJCSloc/pTPFUyzPKXfsY4FPG30OMU8s05ljyFrGm/L3nvGTvf778F3UtyVBKt8z1miZN0ojQ+hk2/d29StO+FRyt+7zQq3l4w3IU42A4sMGGqK8ie759kjnMhB6zo0hpRM/dnv4xru6axg0TTZOr6gxf5PKr6iz9Mb0yT13OMMqQIcbrv715++7y5Yv3l73z46OlFWWchkR88hutujZZpU7cWIDpVr/agQa+EU1MCQZfOY6tE1mjZ6ohJZgALCdm23cYvj95g3t78GlTcR/jXdw8ODUG14i0ecrIa6UZPpBy7SuK9pBXAC1+HBt4AOzt9LNuERFOHzHh3g8CuZn7PIbkDTkWxVkyTsYEvXmPSWSPcOwzMamJ0yzmteAxbszxEdx6xtpfsTHBwZFiuOjBJt5atDbvvEfI6/NNpNB+yrsP3wFTdgv6Dt/oisnDxYmzQzXGIMfB69sdqZPllssbqJivDVjpSwffQx9vo4nIJ9yB8qYZ44J7hMDGayg4YlfBXqYBfQvV6CGnyH/mXQJ7ZMwryvQKq4R2fTFsNeXUdccqUQ59MffzimL2E40BMzvVnqKzYPdF6Ed9LJpOO3Oz/l420p++bQwqpqGB5/Jzd8xhwl2qSsO44Ib4EOkObZz34ywiqSxvIoI4zAh1Zdw47YYRljcvehF+RtL/3VM0KmwX4HqOg1gGPxtEILS3mGHlOKP13LxpDGB+iA9kqgGNmdOwNMxgsatsJIqy8DAh6x/xoPzknj9irxnANtGOTbfbcX2INOwnkpD/4JOSqAljuGnGXMHA2I4LyVj4Dcc1dy6OPxfi+uYWX31D/OynUvK8TwKotykaXlbw6Wewl4ntIdVHjDY7lfF+DvmEyabjRtPFfwHTQcL0', 'schema.py': 'eNqNVG1u00AQ/R8pdxjMH0eAW/HTUlAjFCQkBFXafyWyFnuWmm52rd0NIgqWOAQX6RU4Cidh9sOx06ShjiXH4zdv3ozfOEmS8Wj+nYkFmrWwYMpbXDH4++s32FsEY5msmK5Ao11rCXbTIHClgQkBSGlrZjFrNpSn68aabDxKHCPXagUVs6wUzBg0UK8apW0fegm8RlFFJNHW8msHmsnNeOR+Fzv4eOQv8PYWy7sgNR+PgA7JVpiTTh1uG1euyuGLUiJE8EeDpXUx4oUpfFQSwxNW2jUTh3GrBGomS+LlQjELP/3DPYxUNpSlqGs4RCvkUBQULYrUoOCTKNIdNEq7Ng5+Obu6SqDm4CBZUAwoDELybvb+Q9LnNExbl3LDk5ttIGiXsPV5rvE2WfbgjrBrGGrjZHrRAx073ow1Dcoq5UmXMd3uEbTJ5JA9DO3p3AEfmcPNM32UeTf2p5NTyvTP/XY//Si5f18nudLtDthOhhTR+gnQ+cJfsm+qlqnPnzzm1H6nYlnLzF1RVwOvGotNwWsx9G/pDG5yELWxNwO3L8kFfmNS8hijQMFpmEpvpg4Z1aLWSgdX7lkW4DlNwbphXF3PL4EzKlqRz4HsXXXmvWi0alDbTe/l4M1gZXj1Bmpp84PBmPUqLTsbu29DSbgw9dDN5EQFqywT/ykgUKZPpDOl0tjT+fXNj6yIGxTQGZ1DGmA6hfMHDon1z7Pzw6YHq3s2oBl+CWgwK6Y3vRx6MYMKopYYl/uavBHXOtqkzeN9qNGebfsabXRJfD0AqW877pj/n2evObl4+UjrD/r0SvpNAJgvFp8WnQKfsbdUx17yKUrqOy0nR1bqs4y75OEE+AcnCfRs'}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('hotswap.kicad_sch', '/home/user/Desktop/hotswap.kicad_sch'), ('hotswap_spec.csv', '/home/user/Desktop/hotswap_spec.csv'), ('mosfet_soa.csv', '/home/user/Desktop/mosfet_soa.csv')]


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
