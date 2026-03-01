from pathlib import Path
import sys


REQUIRED_PHRASES = [
    "Do not try to land very large single-file `apply_patch` additions or replacements in one shot.",
    "If a patch fails because the payload is too large or the context is too broad, immediately switch to smaller, targeted patches"
]


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    agents_file = repo_root / "core" / "AGENTS.md"

    if not agents_file.exists():
        print(f"Missing required file: {agents_file}")
        return 1

    content = agents_file.read_text(encoding="utf-8")
    missing = [phrase for phrase in REQUIRED_PHRASES if phrase not in content]

    if missing:
        print("core/AGENTS.md is missing required patch-safety guidance:")
        for phrase in missing:
            print(f"  - {phrase}")
        return 1

    print("core/AGENTS.md patch-safety guidance is present.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
