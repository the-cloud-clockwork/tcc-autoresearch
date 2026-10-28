import subprocess
import sys
from pathlib import Path


def main() -> int:
    paths = subprocess.check_output(
        ["git", "diff", "--name-only", "--diff-filter=ACMR", "origin/dev...HEAD"],
        text=True,
    ).splitlines()
    python = [path for path in paths if path.endswith(".py")]
    commands = [
        [sys.executable, "-m", "ruff", "check", *python],
        [sys.executable, "-m", "ruff", "format", "--check", *python],
        [sys.executable, "scripts/size_gate.py"],
    ]
    for command in commands:
        if result := subprocess.run(command, check=False).returncode:
            return result
    directory = subprocess.check_output(
        ["git", "rev-parse", "--absolute-git-dir"], text=True
    ).strip()
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True)
    (Path(directory) / "ci_prepush").write_text(head)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
