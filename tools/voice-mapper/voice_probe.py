import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("gpk")
    parser.add_argument("index")
    args = parser.parse_args()

    gpk_path = Path(args.gpk)
    index_path = Path(args.index)

    data = json.loads(index_path.read_text(encoding="utf-8"))
    voices = data["voices"]

    raw = gpk_path.read_bytes()

    print("=" * 70)
    print(" School Days HQ Voice Probe")
    print("=" * 70)
    print()
    print(f"Voices indexed: {len(voices):,}")
    print(f"GPK size:       {len(raw):,} bytes")
    print()

    for voice in voices[:20]:
        offset = voice["offset"]

        # Buscar algunos datos inmediatamente antes del OGG.
        start = max(0, offset - 64)
        prefix = raw[start:offset]

        print(
            f'{voice["file"]:>8} '
            f'0x{offset:08X} '
            f'prefix={prefix.hex(" ")}'
        )


if __name__ == "__main__":
    main()