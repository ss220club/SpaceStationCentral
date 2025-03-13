import subprocess
import sys


COMMANDS = ["ruff check --no-preview app tests", "basedpyright app tests"]


def run_command(cmd: str) -> int:
    return subprocess.run(cmd, shell=True, check=False).returncode


results = {cmd: run_command(cmd) for cmd in COMMANDS}
failed_linters = [cmd for cmd, result in results.items() if result != 0]
if failed_linters:
    print("❌ Failed linters:")
    for linter in failed_linters:
        print(f"  - {linter}")
    sys.exit(1)

print("✅ Everything fine!")
