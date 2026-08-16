#!/usr/bin/env python3

import argparse
import zlib
from pathlib import Path


def extract_gpk(input_file: Path, output_dir: Path):
    data = input_file.read_bytes()
    size = len(data)

    output_dir.mkdir(parents=True, exist_ok=True)

    offset = 0
    stream_index = 0

    print("=" * 70)
    print(" School Days HQ GPK Extractor")
    print("=" * 70)
    print()
    print(f"Input:  {input_file}")
    print(f"Size:   {size:,} bytes")
    print(f"Output: {output_dir}")
    print()

    while offset < size:
        print(
            f"[{stream_index + 1}] "
            f"Reading stream at 0x{offset:08X}...",
            end=" "
        )

        decompressor = zlib.decompressobj()

        try:
            decompressed = decompressor.decompress(data[offset:])
            decompressed += decompressor.flush()
        except zlib.error:
            print("TRAILING DATA")

            trailing = size - offset

            print()
            print("Extraction completed.")
            print(f"Streams extracted: {stream_index:,}")
            print(f"Trailing data:     {trailing:,} bytes")
            print(f"End offset:        0x{offset:08X}")
            print()

            return

        consumed = len(data[offset:]) - len(decompressor.unused_data)

        if consumed <= 0:
            print("FAILED")
            raise RuntimeError(
                f"Could not determine stream size at "
                f"0x{offset:08X}"
            )

        end = offset + consumed

        output_file = output_dir / f"{stream_index:04d}.txt"

        output_file.write_bytes(decompressed)

        print(
            f"OK  "
            f"{consumed:,} bytes -> "
            f"{len(decompressed):,} bytes"
        )

        offset = end
        stream_index += 1

    print()
    print("Extraction completed.")
    print(f"Streams extracted: {stream_index:,}")
    print("Trailing data:     0 bytes")


def main():
    parser = argparse.ArgumentParser(
        description="Extract zlib streams from School Days HQ GPK files."
    )

    parser.add_argument(
        "input",
        help="Input GPK file"
    )

    parser.add_argument(
        "output",
        help="Output directory"
    )

    args = parser.parse_args()

    extract_gpk(
        Path(args.input),
        Path(args.output)
    )


if __name__ == "__main__":
    main()