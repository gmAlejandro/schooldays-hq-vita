#!/usr/bin/env python3

import argparse
import json
import re
from pathlib import Path


COMMAND_RE = re.compile(
    r"^\[([^\]]+)\]=([0-9]{2}:[0-9]{2}:[0-9]{2})\t?(.*?)\t?;$"
)


def read_script(path: Path) -> str:
    """
    Lee scripts de School Days HQ.

    Los scripts encontrados pueden contener UTF-8 con BOM,
    UTF-8 normal y texto con saltos de línea Windows.
    """
    data = path.read_bytes()

    # UTF-8 con BOM
    if data.startswith(b"\xef\xbb\xbf"):
        return data.decode("utf-8-sig")

    # UTF-8 normal
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        pass

    # Fallback para posibles archivos heredados
    return data.decode("cp1252")


def parse_line(line: str):
    line = line.strip()

    if not line:
        return None

    match = COMMAND_RE.match(line)

    if not match:
        return None

    command = match.group(1)
    timestamp = match.group(2)
    arguments = match.group(3)

    args = arguments.split("\t")

    while args and not args[0]:
        args.pop(0)

    while args and not args[-1]:
        args.pop()

    return {
        "type": command,
        "time": timestamp,
        "args": args,
    }


def parse_script(path: Path):
    text = read_script(path)

    commands = []

    for line_number, line in enumerate(text.splitlines(), start=1):
        command = parse_line(line)

        if command is not None:
            command["line"] = line_number
            commands.append(command)

    return commands


def main():
    parser = argparse.ArgumentParser(
        description="Parse School Days HQ extracted scripts."
    )

    parser.add_argument(
        "input",
        help="Input script (.txt)"
    )

    parser.add_argument(
        "-o",
        "--output-dir",
        required=True,
        help="Directory where parsed JSON will be written"
    )

    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    commands = parse_script(input_path)

    output_path = output_dir / f"{input_path.stem}.json"

    result = {
        "script": input_path.name,
        "command_count": len(commands),
        "commands": commands,
    }

    output_path.write_text(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    print("=" * 70)
    print(" School Days HQ Script Parser")
    print("=" * 70)
    print()
    print(f"Input:    {input_path}")
    print(f"Commands: {len(commands):,}")
    print(f"Output:   {output_path}")
    print()


if __name__ == "__main__":
    main()