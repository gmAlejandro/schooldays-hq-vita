#!/usr/bin/env python3

import argparse
import json
from collections import defaultdict
from pathlib import Path


# Para cada comando indicamos qué posición de args contiene el recurso.
RESOURCE_ARGUMENTS = {
    "PlayMovie": [0],
    "PlayBgm": [0],
    "PlayVoice": [0],
    "PlaySe": [1],
    "CreateBG": [1],
}


def classify_resource(resource: str) -> str:
    if resource.startswith("Movie"):
        return "movie"

    if resource.startswith("BGM"):
        return "bgm"

    if resource.startswith("Voice"):
        return "voice"

    if resource.startswith("Se"):
        return "se"

    if resource.startswith("SysSe"):
        return "sysse"

    if resource.startswith("Event"):
        return "background"

    if resource.startswith("System"):
        return "system"

    if resource.startswith("Ini"):
        return "ini"

    return "unknown"


def resolve_resources(input_path: Path):
    data = json.loads(input_path.read_text(encoding="utf-8"))

    resources = defaultdict(list)
    occurrences = []

    for command in data["commands"]:
        command_type = command["type"]
        args = command["args"]
        line = command["line"]
        time = command["time"]

        positions = RESOURCE_ARGUMENTS.get(command_type, [])

        for position in positions:
            if position >= len(args):
                continue

            resource = args[position].strip()

            if not resource:
                continue

            category = classify_resource(resource)

            if resource not in resources[category]:
                resources[category].append(resource)

            occurrences.append({
                "command": command_type,
                "line": line,
                "time": time,
                "resource": resource,
                "category": category,
            })

    return resources, occurrences


def main():
    parser = argparse.ArgumentParser(
        description="Resolve resources referenced by a parsed School Days HQ script."
    )

    parser.add_argument(
        "input",
        help="Parsed script JSON"
    )

    parser.add_argument(
        "-o",
        "--output-dir",
        required=True,
        help="Output directory"
    )

    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    resources, occurrences = resolve_resources(input_path)

    result = {
        "script": input_path.name,
        "resource_counts": {
            category: len(items)
            for category, items in sorted(resources.items())
        },
        "resources": {
            category: sorted(items)
            for category, items in sorted(resources.items())
        },
        "occurrences": occurrences,
    }

    output_path = output_dir / f"{input_path.stem}.resources.json"

    output_path.write_text(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    print("=" * 70)
    print(" School Days HQ Resource Resolver")
    print("=" * 70)
    print()
    print(f"Input:  {input_path}")
    print()

    for category in sorted(resources):
        print(f"{category:12} {len(resources[category]):4}")

    print()
    print(f"Total unique resources: {sum(len(v) for v in resources.values())}")
    print(f"Output: {output_path}")


if __name__ == "__main__":
    main()