from __future__ import annotations



import base64

import importlib.util

import shutil

import tempfile

import zlib

from pathlib import Path





DESKTOP = Path('C:\\Users\\user\\Desktop')

BUNDLE = {'eval_inner.py': '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', 'collada.py': 'eJztHF2P28bxXb+CZV8omyf7bCMPQhQEcNwiD7aL3KEoQAgCT1rdMaZIlaTsk1P/987Mfs1+UJJTpy+tgPjI3ZnZ+d7ZD2bbtbtktdoehkMnVquk2u3bbkjKpmmHcqjapp9MVNuuHB4mW4TflEO5rsu+F71GME0SYjjubd8N/K3Fu3In+n25FhLicVfPxNAJoaHe1GInmuEWm8o+eXNrBm4Ou/0R25r9ZDLZiG2yavqsa9thOp8k8Ku2Cb7NhvJ+1g9lN/SfquEhS39LFQD+OgEiNslv6TqdM/B9XQ1Z+iXNk+tp8XxZXM+XXyYBfJp+0UNv67Yc+mwQj3p4BVlQT/Y4TbZtlzwmVZMQVAJvaTpVQ02XmlDVxMlA++VEtlWzWSFAti87UF+e7MFMedL0eQIA5aEeFu/aRqgxmnYjkkUiYWeInGn4qVYlwVR9gmg4LL7PiAfVGOhUDcSlMEia0UNTDat+XdaCLEcjSkLYAzyRSYijdPbs2XqO7jXAX+xOLYOKvtQ19s3uBRhwJwbRAVh6PXueTqcoB9EFlsGTpSyi7kUC/ZqlTrn4Cjy7qx6z8rECrZXNfS1WG3Gv2MNWYK/Zz8q+7LryqOA26OMLaCZWvns1VQrudgAt2YPOumrK+n6GzYQ3ZWpGyEXyfPY8UCggiqPIXo2N8pgnxzz5DAMRd8+ImOQWuYd2DNZZV26qEkLFikQwa92/blWfbO91e181vP01tIPakqtkPXGZlPow3Bfmid4ekycJ/vc6eZqsc3o80usVsP4k6WXTZwVxlE2gjmXu0jkyOgrxaGgR6aOhc0WQcTqfDZ0rPdpnRufRNn22pCN0oIna1T/XDgR79G0ne6ba/eoWokH7HsbLSkAKzBMbKcoD30r3O+kRmC3WD1W9wYxRV/1gKbIcCBkPaBFcJPtdXS8NJDgoAS+SVHKYzh0lfCxrdBedDRVJTGYOGJCpRZMh9BSJXX/nksEf0HfjC6Ejcs460T+Ue1LCq2mMTAHWeLlMniyYDqNw1xfCvbgADq3zNvkR4U2fqJn+hg5isC4H8W1U+DLU4O0FDuLAS0Xl8HCtH6Soi6SAgQ4C/N+KTM4lm8G5kJHlqBZu4zogOn+Y/DdfKf8Nyg9BCw8g/zU9gPwvUH4cZ1S6m7h0NJF8I/FeheLp0YMJC5GKOdqPnl4unSnyrU40MNv3YtW3h24t+gyqsAeVabBICLJNe8Bw/O2LSSsSEU1vUGmeLus6S9dz2Z2yCR1/snVVbYCWfJbzdLVJrfykmhUFvQWTJcB6zjrZ9I+/cg1y9MBZgDOI9UNT/fMgVut2t2sbLCMUsEeDJuCBsQnkODus/jHDBeUP/tZtM1TNweaFHkxDRRbWcRpXCi+7qEpJp5YXCi3uK4wRz2O69lNvgrQvqmSeVDBPScJLMleFloKUcy8y8HLlWwA8zRXY1MnyRLFsNgSJL1AET5MfgjjTIwfeWUAP4DgZI0fw4jrW+MJvfIKtL+fLMKegNNBJ8sDoTr+FBn8tjBmXVEgqWBUHAOBGwkfRDZUXCio6mBcHcaDRRiNBA/ixoNtlNOi3SDwop2TwZ3yN7N3sDwPxQtlZU2d8EYTPlBrPYisXFbsSBlmn0+RPkNn+9v7m59uf379Lw6wUMIM/HvYBaZ0ocB1Toy/us/TPqZsO0ZpM/qWJcakvQz9PiqWLedeJ8sOI3WEsCIgDTsIZ6KUiS39ctwdYgjnmLqRfrQ+dzC/PbXGFwKRhiWYVsm/rI4lLdAuFO9dEnkpU67C6fSE7XGPa4IWZSY55BbXZ3FfSrNzvBSS9AkcvcC6jh8o8wLjXS3dCCAJh31W7aqg+XjArKCNgkrp0Opk4vr8r9xb5XAQSquVOGoYaiXtEF48rDPSsE1u+yJdZio9KfoNQftbz8pvUkZNoFDXugEDIdT29ascsBlOxn7QU29iK8pg4pRLdSB+U6Ab2sjIds0aFexXS0WvKQSk6Ao6jn+/bpk+/jKQUSxLDtrexgL9d+bhqt1tYkJuYMB7rpB/L9yX5RyebWLIwecj1fM0ETq4+juxEaZ/z6VWONKyAIfE4gjqKJ2uf35nMHLXBS2YbciWKVwyS7nVsZ1oJGji3cuh4mQazh6RxzsqmSmE8QsZw5iwIMSKG1TXuMDkks8zwJBmRtWLA8YrBoIco9wJmjfXJc//+5pfbN/9AhZo558vUXXhj8WVbHMEddi+r0xSK5lO9GoNzij6OygtOHnLwo1O6gjxnGTNqWG5l427gwMUtESBZc/hVgQ1MqAHALK/fv//lp9TucUSYncGcNmQfxHFRl7u7TZlUg9jN6V8oBKcOBlW2XopBnlfcaUJe7WDR0jSsE8IiwY6ug4ztO8gc/iLM4ZE15dQabFuuhScMDmOaC0lw5YqwnHAfsXsFOn+7IuL2Onoc7RnzTV+dbyFu1vN9Kifh1E9j5BC4MR6sDZAwrAxe4t6XXB2ElR60u+KxDmTjlJA+SvsBoG+7Q7iPgui/Wv5eRhjB313ZY3hKaZ4ChmY8Cv2x2jyu9i3agRCfumEfxcF0otFgHWS0FOfHCPUXWILHmSC2TXXq/4B57Ys4M+FQhR5/OQ03L/CHuvqQ23zA40WnIFSlaA470WHVa21yQo4h0NYJNSne0QGKD8tAhMGIQP6tKX9v9Sn346+uQxEBof0QZ5OiSg8Gw5/Qj/UlHJIp4JQGdOAykayQdjBn+8fUWd80ZtU64zwFCThGBpnrw/BFQU3XJcHrLYm4pseXRpyJeArBnq/NIQZIWpcGHbEpWMksw1TJ88MlET0eruuHQ4PhTk4ervXUTkwc1Sz8TmQsVAgPJhqvcLLWfzkraBN5US4Z0xxRzMoyUoY4dZ+IcXI+TQ9fQpDfFcXGsRm7TAJvXlRztLNBQNhQOuB4xJhcvaEL4woHeyNVhZnuHVpy6+0cMbvB3mvflz0s3/RePfut4prYOb1+28fWbvhzMtxerVeDHW7N7bdNACqYRuqZ0VoGf/9BCKvdeuXc3yvY8diJbpJx0f8f6lae/+1Q95eMNMq5xaLZI6OqWq4dboS3VJcetQhWOu5uFVuixhY8eYSk9DhOmJhm2OA9AS4grtu224ADLQpAIybwr9KHWh2CGuBp1lefxTJOQA5PZAL/8HhaYX0W8BV1Q0DKE4ODTH2u9pllLLc+EK1cNdNO3zK2b2E3OI336ha1vFSbixZwMpn8aK9a0b/J65935b3KQdVmjjlJ7p+Ww4N8iyDdHDoUQWERAUUo+RftnkSRSrzI1b34Se0JKxqaWAzlbblXwBJ3bonEwN9st2I9hLJsqu32AFNg0t79CgDg7cQjeQMer9OFpvVxLs/wlAgcqn+omqoRfX8KpNxUzT26CA3sgUSFGwQEXR3y25Q7Yd+ElEpJd0LBmuC7Vk8q/XF319aWFCx77wWQ0pAxKiwRSCIyWucYFDCpoxezZhlFQSeL0jntVhcWYOlAmDCMwEW4+6tod2LojueUZp1e0WViIWGXmtUYnRAAT9WwWmW9qLd5cq+AcrykQWrr+aU40jMAzjQcmFw/ugAGXd6UUs+QNArL0UlO6FIOnl6hrLm8iQOeS4x1FUzej7saYXzO6EBNIbs9SAj74I/boWnrCz/wGAgDQ0pJ4MHtVHxAr3py5Dsro8+/ouUQulmLZpxKj71SVYDURxWiYcKxejVY7x54yUDM5B92akUJsF/dHYGYGknB0DgM3p7ayhuZylXbbUXX7jikvpSgelev3799+/5d6ty11JhjNyvfOAwDcxOeeXt7QK3SK2vBuawRn0DwUpX2NBQv7HV3cHlDupvqVQcensyMDbl6YAhactUfXr1wENkVTe94Gq0iLcA2Pzgu7X+Q2+CdYrsF4pDRyip6eZ6sZquMG51kzMyA+rItHetMvRo8vPEhdT+uBj3jRRTBUUcVoU69pVn4RhBHJ12wyzikCE8Sl6pyGaMXzaZWsXPk3mMoatVR8tR74ObSDZ1bWidzLuS4bm9RvtbxYY62mjZTd3j70YzA3Bo3g8avPspjKDBuP5S0nZbiQQZMkXR8+tA29/hwV1dN4x+iulzRGE6/3U1CkzPgr5ReVUFcctWkx2bEjQ0UiGsBBy/qeOhg+E2AoswRmHkJxvPrdVu33Uk8ggijwRlyPBqU08tw4DgyU1mmgkwgMVFPyvelh1uCOYsC39k5JWsJKHA1AW97mKlhVBZLZzgAiczcFjS4ckNFhxrWuit5FdMvgU+5AK+RvUi0qFEm5VU0RdoCu7f0Ttk/gjNifTYUv7WPd9Nsl/kQIa5PV0HyFr6HbLL611sruKjnm8mdvrYKIXaiFrKprvRd4WGpu2Tx1zHHU6Y2WK6dGd55O1vgk3b+Rjbjcp6xGF8UqxxpudksTL5kd/BlgC3UX9vBQ2LB7GEhDF8L88Q7zWJxwc0QnVpmdftJdNnUfgCgVu5tXZebcrQGxhW8X/hiG060+DGWlUWgH725nVGZS5/08Duj7UCBKOgOLr6ySqAhf9bfU5lmdvt7Ef94Z+LyJaspd4+XV1i2MCV3w61bqrb0zrP5/IdqU/oCqK7uurIDZCIDDfQQvchoK0VL1S3V/XZcMAUFLdHS5aRXa1kCY1XnqWKLsIGi3GMxlWZuh/MvLBmdmp1YfAtSjKYUJhmu/UKDLbWKPPPJ0PHspxrHDMgWO2csqAhBi3yK2VD22DuCF63VQp2pobTS5Os0MpLWjHybSdXIF083fNXvXIpTzWP60QCXaMgQgzb9HNOSoUkDOiNEl6YBntoviGDaiGCDeKHRDwGuniEqKpzX2nDeXOFY2MxmhvBW0h6dIxx0x37EOyJLIQ5dHV7K82/lSfapeJOPGZM4d3WVJzEXcv1CO5tuCIKUkY9+/8T9qGDAS6ZtzynVBlXl51zbPuaWemvrEre01KBRI8b8EvvkaA75kz5JOMofI1jWHxVx14r67myArB0SISJe6Fwr/pqL0GRIM2rwYal3tsn2EvUeZabkyK3kOWMn4mFW/drFNNnAxRTt0L18hygU5JLvctpyAPcYoRTpXb8xHxP2oT8pXznjSbQbF/OcrfrEmF2NJgxno6rdROd9w5rdH3W9LpwUtxohfqZoBS0U3JJTdgT/WPUHCFPahTwjPQfFUOLvFymFI3hj/BHKoQpeP6vb5VY1v091tiaHSlfGHXZGP1Q9y3vCFTS+Q+lJpaVABw+FYJ+uE4QRI2CL5jBgfUzfCz0gcOPeWjaAEPwLTwCZ8EJYvX2/KJZhp9y8X1zyNXGIrPb2LSMuSJBkRkMn1Jne7edQl32krH+Xf6zMONR38igoxv3UnI6Yk1frj9QVuXfh3Pkz1c6JgTqxlf4rZRivT0ax9Y6yiSz9DUpQ+zIVGMST1dRJbegzHq4WTdbfChtXjakX4qNjt52DKmcr/pzGRoUnotEPAPjv5LWckXKf/+SHL/2A8Ya+LNnVaXl0WJjJ7nA9qUd4Fv1i1ejPrgPGrdfH+05dcaUTZH6A6RXSOK7aSSXQS7WPP3IDon/WBvg7aQf8BSU2PyH3uJVH5ZLbXLExwmrU6flRMtVZ7LjYo8NmCq8slzN8+GnDH1gr6FNQGNSpEk6V3vqMtIjOw5eWH7z2cAOF6UKrl457M/9YFzfD2ILM+18Fgbn3C/hvOpGKCwFoVG65BX+RwcF9ZsFfZDc1u6+myTYT+wv6N59MJ+ZDDQolnyt2VWHBnqeTfwNyC08g'}

CALL_FUNC = 'eval_outputs'

CALL_ARGS = ['__DESKTOP_DIR__']

INIT_MAP = []





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

    spec.loader.exec_module(module)

    module.__engiworld_bundle_paths__ = added_paths

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

