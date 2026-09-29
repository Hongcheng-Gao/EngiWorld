"""Shared utilities for desktop drivers."""

import os
import subprocess
from pathlib import Path

from hai_drivers.desktop.models import RunCommandResponse


def run_command_impl(
    command: list[str],
    env: dict[str, str] | None = None,
    cwd: Path | str | None = None,
    detach: bool = False,
    timeout: int | None = 60,
) -> RunCommandResponse:
    """Execute a shell command and return the result."""
    if cwd is not None:
        cwd = Path(cwd).expanduser()
    run_env = os.environ.copy()
    if env is not None:
        run_env.update(env)

    process = subprocess.Popen(
        command,
        cwd=cwd,
        env=run_env,
        stdout=subprocess.PIPE if not detach else None,
        stderr=subprocess.PIPE if not detach else None,
    )

    stdout, stderr, returncode = "", "", 0
    if not detach:
        try:
            _stdout, _stderr = process.communicate(timeout=timeout)
        except Exception as e:
            return RunCommandResponse(returncode=-1, stdout="", stderr="", exception=str(e))
        stdout = _stdout.decode(errors="replace") if _stdout else ""
        stderr = _stderr.decode(errors="replace") if _stderr else ""
        returncode = process.returncode

    return RunCommandResponse(stdout=stdout, stderr=stderr, returncode=returncode, exception=None)
