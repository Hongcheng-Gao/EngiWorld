"""Build a task archive from committed Git blobs without checkout conversions."""

from __future__ import annotations

import argparse
import os
import subprocess
import tarfile
import tempfile
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--ref", default="HEAD")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("paths", nargs="*", help="Paths relative to task/, or all tasks if omitted")
    args = parser.parse_args()

    repo = args.repo.resolve()
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    selected = [Path("task", path).as_posix() for path in args.paths] or ["task"]
    if any(path.startswith("/") or ".." in Path(path).parts for path in selected):
        raise ValueError("Task paths must stay within task/")

    with tempfile.TemporaryDirectory(prefix="engiworld-task-archive-") as temp:
        temp_root = Path(temp)
        index = temp_root / "index"
        checkout = temp_root / "checkout"
        checkout.mkdir()
        env = {**os.environ, "GIT_INDEX_FILE": str(index)}
        subprocess.run(
            ["git", "-C", str(repo), "read-tree", args.ref],
            env=env,
            check=True,
        )
        file_list = subprocess.check_output(
            ["git", "-C", str(repo), "ls-tree", "-r", "-z", "--name-only", args.ref, "--", *selected],
            env=env,
        )
        if not file_list:
            raise FileNotFoundError(f"No task files matched: {args.paths or ['task']}")
        prefix = str(checkout) + os.sep
        subprocess.run(
            [
                "git",
                "-C",
                str(repo),
                "-c",
                "core.autocrlf=false",
                "-c",
                "core.eol=lf",
                "checkout-index",
                f"--prefix={prefix}",
                "--stdin",
                "-z",
            ],
            env=env,
            input=file_list,
            check=True,
        )
        with tarfile.open(output, "w:gz") as archive:
            archive.add(checkout / "task", arcname="task")
    print(output)


if __name__ == "__main__":
    main()
