import subprocess
import sys


RUFF = "ruff"
BASEDPYRIGHT = "basedpyright"
COMMANDS = {
    RUFF: "ruff check --no-preview app tests",
    BASEDPYRIGHT: "basedpyright app tests",
}


def run_command(cmd: str) -> int:
    return subprocess.run(cmd, shell=True, check=False).returncode


failed_linters: set[str] = set()
for linter, command in COMMANDS.items():
    print(f"Running {linter}...")
    if run_command(command) != 0:
        failed_linters.add(linter)

if failed_linters:
    print("❌  Failed linters:")
    for linter in failed_linters:
        print(f"  - {linter}")
    sys.exit(1)

print("✅  Everything fine!")
