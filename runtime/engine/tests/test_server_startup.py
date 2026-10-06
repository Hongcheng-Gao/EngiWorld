import ast
from pathlib import Path


SERVER_MAIN = Path(__file__).resolve().parents[1] / "desktop_env" / "server" / "main.py"


def test_vm_server_uses_stable_production_startup_options():
    module = ast.parse(SERVER_MAIN.read_text(encoding="utf-8"))
    app_run = next(
        node
        for node in ast.walk(module)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "app"
        and node.func.attr == "run"
    )
    options = {keyword.arg: ast.literal_eval(keyword.value) for keyword in app_run.keywords}

    assert options == {
        "host": "0.0.0.0",
        "debug": False,
        "use_reloader": False,
        "threaded": True,
    }
