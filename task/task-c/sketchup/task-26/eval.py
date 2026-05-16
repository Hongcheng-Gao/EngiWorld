from __future__ import annotations



import base64

import importlib.util

import shutil

import tempfile

import zlib

from pathlib import Path





DESKTOP = Path('C:\\Users\\Administrator\\Desktop')

BUNDLE = {'eval_inner.py': 'eNrFWltz2zYWftevQNkHk6nMWI6Tbpxot47rNp11nU6TadO6Hg5FQhYTXrQEZUvWaGYfd9/3F/aX7HcOwKuo9LLOrGZsicDBwXeuOABoWdbZjR8v/CLLxRR/r/++f7p/+ET8+s//iNNFXvhRKm79OBa3UTETySKOoywV13kUuoPBd36upBLZopgvCjf05ZBo3ytRzKRQgUwlKP35TPjzebyK0mtR5H6qME+ihsJPQ3Ej82gaSXU8EGLkii9PzsRcM/WVALAoFKevzs9PvjxxQXHoijfgvEgJQzYVhAscCrkUJycvXiiR+EUww2BC7N1GISAvS9BeKOf0DD74MMVMRtezQtijA5AduCP8PxKJw7JCbjQnCc37yBUnhYilrwrx6AkQpjLeV9GdDMW1zBJZ5BEhziVUuIBUfsEaeMr8SFcCuihyqfTctsa8H8QLVchcgMEsC49BmS3mLBSmmjZZT1bEMMrFbZbH4b6a+4HUvJhxFoVDLbuQPv1bzmVQyHJaUWSMJ5WACBHMvNoC0FfwXvOSywL0yiGRj1zxPI4muZ+vPDmdgp36qwiylBxCkYBaG4cijFQRpUEhDBUNfqztBEQwrx+LCWsFKFhzTcFmMDP7BKwu02AlPhnDDw6IyZNdTCon/ACbccXmc1ecLf2giKHC26yGW/FN/cQYb6GgMj/IM9Xw4KHI4MbZ1LjNLIJ+Kz3sXce+UnvCDnwl99EiUxUV0Y10WLc0cg/Rley5A8uyBtM8S4TnTRfFIpeeJ6JknuUFSNOs8AvIpAaDsi2/5kAonzOlRwdZHEPNRFsOD+XUX8RFGAWFpgn9wg8ImKxpyqahQLjFYTVPukjmKwq2dF420RR+6A8Gg0/FazjSfghF3ZA3YdLCh4cIWztblEaFN41i+TDQqcJToHffqSx1Bj+enJ97PwoY4sA90E8v8XRUPvyEB4q5xudTWGVps5PoaB22g9cZXDCPp/j+gXgNvju5ONOzmOkeCiIBp9HBw6fi13//C34wwsdQviwpXzLlD0wJRIMXL1699d68OmdQB6MGJM4CghIOwpaCk1LN4PTs4s33r775sh5z+FjT41vTa2cvA3Rw9vYNxnTpe0Zw3nqocxMbYf/+PuAmXgdZLgM/D++Z9eCLyssG/F+cUm455sihKDsWqsj5aU7OiYw3ybKYGxJ1rXt7uDDeU+DVnDhhqWMRI5KhSXZn28SAN0WkZ/lqTJ3OgOnRJfwwtJWMp0PGMTTzD2naoXjwwHM0a/oQmavncLFsyTS0WQx7a6RjJvhinmdzZPRVPR3WFk3Isza45xKhn7LcdmMmnS4wzA5cPZAX4wAR1gS0c8IC+SP2FClqx4xwchFNNbManpCxkuSMtaqQPxHvXS5xlCKZjMWltW+JB+Lzv1xVXX1A64HV4FKZU0uIy/XedyevX+8RokpghrL31ck353ubKyGsFovWZ2qtA5cd6vmjo43AA6yxsZxB74Ql4h3dgzZnIb6XCp50LBoYe7VmoHaRTi2b7QBlrXlcwzbH7mi6cWp6p2sl65fUct9lUWozRufjhD9WtX1dl2HNRFJTfnzfqYA8ySsy72h5ZCfGj3yoJJ27fp77KzsZirBYzeUYLdM484snR1obULfvqpk/l7SI26Mnw21n9l3UMURiHw1F/zju2B44aDxgZrkCC9Iy4zVrq0fVl0fVhbJRGswMGyzg3+uBnHlQftKKi0TEJVekeLVvFm4rBAWtl4HUxbOu3ZgXF3BcukYBFR8Ifl3eVFWJjZKPXBwVhwTuGz+K/UksUZsxgzMu87CyrEoZ13tEvsdZdCj2iLfyeEq02RfDR8gxpHn0YRKvJhaI3wtg35RS8jdqegr3qzoxUGVvp1mIJPjtsALqQcLgfUPTCYZ96wbZfGXX7g3joETziyI3HAhDHi33nHamaMhTf4hjIr6o/Ik4uHq80yKWywBVAso9+kLRsM2K4rdqJD6sB/C/lkUTXRTuDVkpDmmn08mqa3RbVjsXUl3UHRPMojhEasW4yysedXnVhgcVRap0GDtA6WPqMJfLUPdr41QXYOhsS0Y+BzmCmVt63xZJnAWwFxQHOgK/RUDok5TQg01pYNUH9oP26psvSd0CJa0sOG/3Dvlt6/VasfIS49SYrJ4Y0O1eNm33vdwfXZEB2q06zbOZt3g0wkuHSZ8u53mUaF/IEpceeGug+gW7USY9Kp0gid7VG8VdqbL7gQQ3yqV9KaXAg90KpP1LlC767RCFy51IvAjFwdIBDDi3TO2dOMDkfwYyY48GkBmbw768we4FjzCIsm2SlLL95cHVUIwc56ofyy1Y2MTpC5G4b5zL46E4fnTVb4Hapi5vhUP79hKCXGEJp5RvO9tTkMrrYf2CIpWWxcZ6pybK7F0nJU48cJzWQxRyxvmbNdzNqZ36qxW30ex8YHRjcSh/9lNvOsk3/q0MtiNz8bpC1CgJWM2dpeXPTLNjqhzLWJ3raege6btM5n3WpSFY27FBZ5p+C7MIoPyADIMyKSjKCFRWaLiNbEC9nH2VS6g6eUIvv8O6auGVpFnPwM8+Rr1I54MfozyU4Ovpo0Nl628vjHJjNhXAUtXOzySa0Kf0nilsGYqZrpPrgUNh1QeRVlUUkuXKEXIJ2ygb/c0NX+DS9tCicwxPU1hD8RVWPizc0wZPZlUd8K3R0txzGCOoQJu6tTKSuWlxNn56qr8Zx6Bv6aPzGLmNEPSePh1tAuQWIfM8y7FpkZ/k/ah2MnqTL9oRju1VjNzOPlqfsTkbzkBKPBR1tznzQ5/5hV5rF6+qogB59dsyoXEvDmY4neo6vnlYul2Tq3uetmVwbANueL+8c0/xR+zOicKjBNC0uz5fp9bfNn4zGDS23zeLlWZbZ9EcAbtnoW0yLzV67b4xa/f5ZWtduuJsd07ZTuMxqWwy8RK0jWs2Lp5tH2E5PqhJ/GWbxF+2SGBy4mEo9w3X+3c023fEK3MqyPs3uuKYZMt7nij0WNyJskkwFDwQSR93mrTorZr9o6r/p7L/rtl/WPW/1P3Ze28yAQXN83wsqqNQ2pYS7+22u2ZbM7VUXmFNoAdvdLA8cEfLo0a5wpPVj/BjMtbb8drIduweTTfiJ/M8Ms8/m+dD89zYcll2dd1BJ8346Msc/eOIW54JlHBiXSLeOAbQR0g+9sT5XZdFRX1Ls3VDdJ94vkKc8QkFxTHVSgmWM1kdSws7icI5VlI+0YgQtnS8TXH5lm39s2P40MPbhz+bS6Jn5rqJpVN0K9O4c4rjUhp3YLLhFDuHaVZvlTrRX2ejG9B0c0WdVhMK65utlKD7lrqvkwtaAPrr8LL2xrz866pd8FJJrHur2rhLESxBcOA+Fg+EDZAUop8RIvxwuqSrNumoJB1tk961SQ9L0sMtUkkA9IQIbg2hS7IyJKOSZLRFcmdIDkuSwwbJxkSLvmRt7HuTiE9FW8aNyLi5n15L+wJ5pl3lvmt2/tAp1GVAhrQjyArZHQhvLnk6VJTT7HddqpctqolUvacd1O4R4pF8Ouhu27HlGwp2V6CU6SJBgi+kXTlRz8aCt8zUd0muQMqDFNtUdzXVnaG626YiucDwAXH9jAbh1x0kfECS9u1RQvHcSNS/PamkDXd2s8ZLuZ3uwRRTYBd0wVehecnwr6J5C9ZzcMd+UcacHQ3Fu2E5tuRan7Fsb796TwdMHqHBcOAuUptWOa1iqQ1hnMcB2voGrn+fnovG6LvG6Jft0c4fEvX3CmbCqocHZRETe1WWHfM954PyDvPRk3IlNxl5LLju1jwBf1wNLWtBDbkRmFEOuNRK53XceXl8WGuYmjw6Lx4L65kw1xRYfdfRZrh+t3FEOF6HG0uHEGMPKYBqtk635GyJb2ng3qMnHrIsLYmdM45KtmHnvqXMR+umxJuH61LgjVmlnm3d1DA2LatC+VxKuGnMbAp1eOnx/xn+zpKhhfb+65mgUc9sv+7Ba3j7PZF7hpAS39Kfm5vO/rrT9JIVGLN32NCP5oVgOGxWoNsvutD7JGsmLne2tnKe1eonDh+xhETANt9Z6byqQq+pPOPbpu57KMPGGyf3jIompSN1Sg4qy6EEe92qiLolHaWYFoE5L4yzW0k55DJx+aft6HsHGllNorMOrOCxYLR7SVd2+bYNHaDVg5iLUw0g4Ut6VsRucoSk1ui4MRXVuRUfeiC/q4A5dKB92O95PN7DEB6L/J5o9u3NDzc1va998Ud5qJpt86y10Ukl3T0bxzgsrU97zlIzhFdL/RG9Uzria1ZVz4tbz8SJkb3vfax7xkK+NVmVtz5rfVR+3DR2+9xpU19meozOLr3TU4sJEn+nTNVvfNA9ErGqJ3OjQibKdrYu8DrsaBjTG0ffLht23p+ZQxW+7iGUJum5TaU64pedx/gaTN+o5ml2XX0N/txtnIHZ4tBs40YdF1RiGq0bb3XMedGi1cfea9wW4VIPLn818fNbM6jZyr598jIq1g7cg8cfitJaI0U7PE13M0B7nB3eZgg3wuaw1O7fOVcAv1I8/d2HXfcY5M/HH4BepZVs7v9jIdvAmU0T9o5AFGumLHGP+3A3jvT4qD5Bmindl8+NKYGXbyi6J/k19khpwW8D5+aoXpORAJ5v+m1rfz+McmtYvrE4Jj3svoqayXg+tjCimem2jvjBnRK4mY+/aEaEZ3XqSY8u+NQ+HGr83NpT4JkXIdVsUURxtxWxP6e7gqq9SOZgVza7yfuQfjfuRq+LrVsL84DpKUFUz/AH+rY9fqvS85wP3NSRL+e0dsCZF8UMarVgZySahnLYjVgK/UbGdTFsAwH2zr2J01IS+gf1fUzryiY0hs4jmBa+al4cc1p3Uvqls2Dr5akRPAs9nk6XHrmh5XnkZ55naUPkfgTC1ysFbZ4tI0qD5IXO4L8BFawO', 'collada.py': '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'}

CALL_FUNC = 'eval_outputs'

CALL_ARGS = ['__DESKTOP_DIR__']

INIT_MAP = [('curtain_spec.json', 'C:\\Users\\Administrator\\Desktop/curtain_spec.json')]





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

