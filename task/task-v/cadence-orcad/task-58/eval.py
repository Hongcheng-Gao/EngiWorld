from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


DESKTOP = Path('/home/user/Desktop')
BUNDLE = {'eval_inner.py': 'eNqVVMtu2zAQvOsrWF5KNrbcBj0URhTAQFPkVARFTrVcghYpm61ECUsqSOL637ukJFvp41AfJHM1M/vkltDURIiy8x1oIYip2wY8kdY2XnrTWJckg+27a+z4H3RSBmYr/b4y25F2h8ckub35ckOyeGAobSoU5ilo11QPmvG0laCtTz6u7m9ERIJOi6ZuEciArlfzr5u1nD9vDpdH8uKUu4tcHd7N0J6rXC1PDzwe3h8pT+5W97f/0Away8X629X165zm7s3mAvFJonRJhG2glpV51szrR78kzgMn8+vwXiYEf8GMokPIqeu2jF6F0zWdxY98ChuiiLBK1lslSb3s61GnO2i6lr3lPLWy1lM2aGyCjQasVlvJQjOaQ27RB8UnTzEe07JT2EXdsiASA56RpvNt53tHY/jkJ/ncWN1nIa3D6HoYWZBAjfZdCDp2bUFoiM8q4aHzezpFmZLgUASRVD8a5x3jvewk9pLWxjljd+QQeEc6MiclDgKgJbrARJm2RaOQkNHOl/MPmKoGaMBl1OyQoynn5FU25Z987vx/6UTe30LuQyXKlKUGR6e9CLUbqq0fZCX62jnWv4UycB4WZQrfqw8VHq7AGTu5BIOTeGsycqCtdI4uySdZOZwJeubQ6GAQ4cfIKxuIbSHGEkYfDNbFeWG1T/2jD8MyMVXySUO0T1IPqaLb0wCNs8NPCGxZAJ0p53jXFKuOu4BuUCKAfsPEwvXQZMqKKQbOPXT6xZdir4sf/bf1SSwkMd8+zTGHAehILX2xJ7L0GuLqWSjpNRlHI+4rOosKm+TPYHCT4SCKkDBuuiwjVIhaGisE7fMclx/scEU5bHy8NC2GNZrSFey6GrfXXTjB0EfZplIpIYdvbNq+AQG7cPUQGGUC1A3kFgxSwnJNVVe3jr0YtABMJxM0w54r9JFd4oBbF5a2dIUxWZwczpNfiN7XBg==', 'ground_truth/vialist_net.txt': 'eNqVmlFzojoUx9+d8Ttk2selluRAgL6h0G5nFRVYe98Y27Ktc13tqN29/fY3wXbranJCRjoqv3NOTv4HyEE6W8zJcLHdkfs3ktW7bie5ulyuH+bL3+vNv5fp6mkhPiwfL3u7ny/VevMwf6xeNuv7mnqXX4ukup7cxNWPxWq+7N1vHrud0XpF4pcNYQGh0RV1r4AS5jLe7XQ7ef2y3uzIdT3fvW7q7VW3Q3ukfK7JZg8eF9uX5fxtS9ar5Rv5tZhvycN6taofdvUj2a3JnKzqXa/bIYSMd8/15t1kviL3NZE5S7vX7WL1RM6S+eppKT8NF6vaITMxy/nqkcSrXb1azck+lTMRjPUk3JLfi90zmY2HZXyTXuZxWWRpWVTF4GuafB+mRMz5pd7s3vZ2v+bL15qsf5DJ+C7NqzhLqpt8/D1LyHxTk/q/h+Xro8jlx2b9k+z+TLAnRZi9693tCLVJNv9ZO+V6N182WTjl82b9+vS8/9Lv79+lizTcdjtfqD9zqHi5zuw2dis2cCt/0O1cyP1MvI72u73An+XptUMDualoWTqUyu0ERntPJZzdZg6I19F+2nNnDkRyOyFMZO7J7YSI3ENfbicknDmcy+2IMOmjjCaJTFuRHPRg5kTOSWoilO/J7Wh/nFSDwuFNqDNBKBMH0qdB84VB8wb8rLFP+q7jizJYONBThz82f7l/ODBHzNvGAWwdPNuUfNsRuK1DcJCS2rL5QtmHQ2hbh8h20tS19qAH0241CxHWdgywm/j10LVL6npI7Yp3m08tD9k8sbG/yRKHRnI7On+TLxZhkgsb4yRnvdhVXYn3SAaiogwHmp6KuTdl+ihwEOXvlE5y8fRR/PZReHvToL1pqM8tQiR0248g1yhtHGYRB7Rx+ki5+xb1HsSFNs7gG3VC8VKzcwym+uyS0aECqmvBZ3bJlFIb48DGODotxJHPpzFzLSIzmwkybmEMbuucx0mpr0GOVD1PpsV5+4O90I9yl+pQNeqNYnmh97SUopShFFDqodRHKUdpgNIQpRGuhkEsXC2Ky0VRvfp4ofp4peT1BcPySoHwZOSq7iM+McUxwzGgeIqPPcXHnuJjTw1jezj2ccxxHOA4xHFkkMUkm0E3ahCOGpSjBumoQTtqEK9ZZQDhBvmahQfxb9YajJuOO2bwN+jHDPoxg37MoB8z6MdCAzccf2A4/sCgX2HwL0z+huO3MOgvV1+DgSmDc1MK52gOTe+AXJVz/KKeG+eQ7yeBlDk3ziI3TqNAJyG6EzUFeSvFHa5GVI+YHoEeeXrk6xHXo0CPQj2KkCljciB6UEQQiihC9ZL0kdL0kdr0keLIFsV3fDVrboF4i04YPm6JeIv2HPa3SLqMmvNPB+XJp2VpkZZaWuiDipNBg/AuDPAuDPAuDPAuDPAuDPAuDPAuDPAuDPAuDPAuDPAuDPAuDPAuDPAuDAxdGBi6MDB0YWDowsDQhYGhCwPDKgyGVRgMqzAYVmEwrcJgWoXBtAoDvgrLXxAZj5q/I3YTl8qb6uEsKarB8Ftm8/P9h9PExilzgYOytpnrga/8NSBzfZeFah/uuZ7ah3vA1D6BH4Rqn4C7XO0TulTjE7qe2oe5XH0WCRIEag18Hmk0kIRpiaclXE0CNwo0hHmaDAIIfQ3xQZ0bB/BCtQgCcU9dVe4zGjJ1FoKxQFNZySIv0PkB1cyZh34Uqe97MgECj3NNTBf8sGpawsndSJPThw0QzIYzc5y9jTbOZHCb9iZpXpTnFg9B3r3KzEVilhlFKUMpYHSCjjtBx52g406QcfMiK8+ptUyNG7N1y9NrcZ38ojqGDviFlhcjgS0e6Lw7JXFpm+ld/C21OnhuxuOkap55fz5ZbusUzrSPQY+6X+FUpFmRqupZlElcFUX+zxeUXiC0RH1LtW85sClJmdxqZT2drLAeW1ShTA6t1c9HD6xHyl/vS3HdUO2f3SZV4rZ5ItRY0taWrLVlqyeHjaXX1vJaTLbl8FN58rUMWwyGrU2TuJ1ppixL8282W4dCIFZeJh8ZcurIf8n5H4KdjQQ=', 'ground_truth/vialist_netlayer.txt': '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'}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('HSD_FPGA_final.brd', '/home/user/Desktop/HSD_FPGA_final.brd')]


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
    print("true" if _run() else "false")
