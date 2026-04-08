"""Pre-commit hook: run TypeScript type-check on the frontend (cross-platform)."""
import subprocess
import sys
from pathlib import Path

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"


def main():
    result = subprocess.run(
        ["npx", "tsc", "--noEmit", "--incremental", "false"],
        cwd=str(FRONTEND_DIR),
        shell=sys.platform == "win32",
    )
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
