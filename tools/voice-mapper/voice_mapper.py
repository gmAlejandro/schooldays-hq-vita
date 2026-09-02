import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("overlay_json")
    parser.add_argument("-o", "--output", required=True)
    args = parser.parse_args()

    overlay_path = Path(args.overlay_json)
    output_path = Path(args.output)

    data = json.loads(overlay_path.read_text(encoding="utf-8"))

    offsets = data["signatures"]["ogg"]

    voices = []

    for index, offset in enumerate(offsets):
        voices.append({
            "index": index,
            "file": f"{index:04d}.ogg",
            "offset": offset,
            "offset_hex": f"0x{offset:08X}",
        })

    result = {
        "source": data["file"],
        "count": len(voices),
        "voices": voices,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("=" * 70)
    print(" School Days HQ Voice Mapper")
    print("=" * 70)
    print()
    print(f"OGG signatures: {len(offsets):,}")
    print(f"Output:         {output_path}")


if __name__ == "__main__":
    main()