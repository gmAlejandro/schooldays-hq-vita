#!/usr/bin/env python3

import argparse
import re
from collections import Counter
from pathlib import Path


COMMAND_RE = re.compile(rb"^\[([^\]]+)\]")


def analyze(directory: Path):
    files = sorted(directory.glob("*.txt"))

    if not files:
        print(f"No .txt files found in: {directory}")
        return 1

    commands = Counter()
    files_per_command = {}

    total_lines = 0
    total_commands = 0

    for path in files:
        data = path.read_bytes()

        file_commands = set()

        for line in data.splitlines():
            total_lines += 1

            match = COMMAND_RE.match(line.strip())

            if not match:
                continue

            command = match.group(1).decode("ascii")

            commands[command] += 1
            file_commands.add(command)

            total_commands += 1

        for command in file_commands:
            files_per_command[command] = (
                files_per_command.get(command, 0) + 1
            )

    print()
    print("=" * 70)
    print(" School Days HQ Script Analyzer")
    print("=" * 70)
    print()

    print(f"Script files:       {len(files):,}")
    print(f"Total lines:        {total_lines:,}")
    print(f"Command instances:  {total_commands:,}")
    print()

    print("=== Commands ===")
    print()

    print(
        f"{'Command':<25}"
        f"{'Count':>10}"
        f"{'Files':>10}"
    )

    print("-" * 45)

    for command, count in commands.most_common():
        print(
            f"{command:<25}"
            f"{count:>10,}"
            f"{files_per_command[command]:>10,}"
        )

    print()

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Analyze extracted School Days HQ scripts."
    )

    parser.add_argument(
        "directory",
        help="Directory containing extracted .txt scripts"
    )

    args = parser.parse_args()

    return analyze(Path(args.directory))


if __name__ == "__main__":
    raise SystemExit(main())