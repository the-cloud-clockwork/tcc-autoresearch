import ast
import json
import re
import subprocess
import sys
from pathlib import Path

BASELINE = Path(__file__).with_name("size-baseline.json")


def python_files() -> list[Path]:
    return sorted(
        path
        for root in ("src", "tests", "scripts")
        for path in Path(root).rglob("*.py")
        if "tests/integration/fixtures/" not in path.as_posix()
    )


def function_names(tree: ast.AST) -> list[tuple[ast.AST, str]]:
    found = []

    def visit(node, prefix):
        for child in ast.iter_child_nodes(node):
            name = prefix
            if isinstance(child, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                name = f"{prefix}.{child.name}".lstrip(".")
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                found.append((child, name))
            visit(child, name)

    visit(tree, "")
    return found


def measurements() -> dict[str, int]:
    files = python_files()
    units = {}
    symbols = {}
    for path in files:
        source = path.read_text()
        names = function_names(ast.parse(source))
        symbols[path.resolve()] = names
        if len(source.splitlines()) > 3000:
            units[f"{path}:file-lines"] = len(source.splitlines())
        for node, name in names:
            length = node.end_lineno - node.lineno + 1
            if length > 300:
                units[f"{path}:{name}:function-lines"] = length
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "ruff",
            "check",
            "--isolated",
            "--select",
            "C901,PLR0912,PLR0913",
            "--config",
            "lint.mccabe.max-complexity=12",
            "--config",
            "lint.pylint.max-args=7",
            "--output-format",
            "json",
            *map(str, files),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode not in (0, 1):
        raise RuntimeError(result.stderr)
    for finding in json.loads(result.stdout):
        path = Path(finding["filename"])
        row = finding["location"]["row"]
        matches = [
            (node.end_lineno - node.lineno, name)
            for node, name in symbols[path]
            if node.lineno <= row <= node.end_lineno
        ]
        name = min(matches)[1]
        value = int(re.search(r"\((\d+) > \d+\)", finding["message"])[1])
        units[f"{path.relative_to(Path.cwd())}:{name}:{finding['code']}"] = value
    return dict(sorted(units.items()))


def main() -> int:
    current = measurements()
    if sys.argv[1:] == ["--record"]:
        BASELINE.write_text(json.dumps(current, indent=2) + "\n")
        print(f"Recorded {len(current)} existing size measurements")
        return 0
    baseline = json.loads(BASELINE.read_text())
    previous = subprocess.run(
        ["git", "show", "origin/dev:scripts/size-baseline.json"],
        capture_output=True,
        text=True,
        check=False,
    )
    errors = []
    if previous.returncode == 0:
        protected = json.loads(previous.stdout)
        errors.extend(
            f"Baseline increased: {key}"
            for key, value in baseline.items()
            if value > protected.get(key, 0)
        )
    errors.extend(
        f"Size increased: {key} = {value}"
        for key, value in current.items()
        if value > baseline.get(key, 0)
    )
    if current != baseline:
        errors.append("Record the current shrink-only baseline with --record")
    print(
        "\n".join(errors) if errors else f"Size baseline passed: {len(current)} units"
    )
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
