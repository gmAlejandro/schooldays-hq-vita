#!/usr/bin/env python3

import argparse
import zlib
from pathlib import Path


ZLIB_SIGNATURES = (
    b"\x78\x01",
    b"\x78\x9C",
    b"\x78\xDA",
)


def find_all(data: bytes, needle: bytes):
    offsets = []
    start = 0

    while True:
        pos = data.find(needle, start)

        if pos == -1:
            break

        offsets.append(pos)
        start = pos + 1

    return offsets


def format_size(value: int) -> str:
    return f"{value:,}"


def format_offset(value: int) -> str:
    return f"0x{value:08X}"


def find_zlib_streams(data: bytes):
    candidates = []

    for signature in ZLIB_SIGNATURES:
        candidates.extend(find_all(data, signature))

    candidates = sorted(set(candidates))

    streams = []

    for offset in candidates:
        compressed = data[offset:]

        try:
            decompressor = zlib.decompressobj()
            decompressed = decompressor.decompress(compressed)

            if not decompressed:
                continue

            consumed = len(compressed) - len(decompressor.unused_data)

            if consumed <= 0:
                continue

            streams.append({
                "offset": offset,
                "compressed_size": consumed,
                "decompressed_size": len(decompressed),
                "end": offset + consumed,
            })

        except zlib.error:
            pass

    return candidates, streams


def inspect_jpeg(data: bytes):
    starts = find_all(data, b"\xFF\xD8\xFF")
    ends = find_all(data, b"\xFF\xD9")

    print()
    print("=== JPEG signatures ===")
    print(f"JPEG starts: {len(starts)}")
    print(f"JPEG ends:   {len(ends)}")

    if starts:
        print()
        print("JPEG candidates:")

        for start in starts[:20]:
            end = data.find(b"\xFF\xD9", start + 3)

            if end != -1:
                size = end + 2 - start

                print(
                    f"  {format_offset(start)} -> "
                    f"{format_offset(end + 2)} "
                    f"({format_size(size)} bytes)"
                )
            else:
                print(
                    f"  {format_offset(start)} -> "
                    "no JPEG end found"
                )

def inspect_tail(data: bytes, streams):
    if not streams:
        return

    last_end = streams[-1]["end"]
    tail = data[last_end:]

    print()
    print("=== Data after last zlib stream ===")
    print(f"Last stream ends: {format_offset(last_end)}")
    print(f"Tail size:        {format_size(len(tail))} bytes")

    if tail:
        print()
        print("First 128 bytes of tail:")

        for offset in range(0, min(len(tail), 128), 16):
            chunk = tail[offset:offset + 16]

            print(
                f"  {format_offset(last_end + offset)}  "
                + " ".join(f"{b:02X}" for b in chunk)
            )

        print()
        print("ASCII preview:")

        text = "".join(
            chr(b) if 32 <= b <= 126 else "."
            for b in tail[:256]
        )

        print(text)


def inspect_zlib(data: bytes):
    candidates, streams = find_zlib_streams(data)

    print()
    print("=== zlib analysis ===")
    print(f"Candidates:     {len(candidates)}")
    print(f"Valid streams:  {len(streams)}")

    if not streams:
        return

    print()
    print("First 30 valid streams:")
    print()
    print(
        f"{'#':>5} "
        f"{'Offset':>12} "
        f"{'End':>12} "
        f"{'Compressed':>12} "
        f"{'Decompressed':>14}"
    )

    print("-" * 65)

    for index, stream in enumerate(streams[:30], start=1):
        print(
            f"{index:>5} "
            f"{format_offset(stream['offset']):>12} "
            f"{format_offset(stream['end']):>12} "
            f"{format_size(stream['compressed_size']):>12} "
            f"{format_size(stream['decompressed_size']):>14}"
        )

    if len(streams) > 30:
        print()
        print(f"... {len(streams) - 30} more streams")

    # Check whether streams overlap.
    overlaps = []

    for previous, current in zip(streams, streams[1:]):
        if current["offset"] < previous["end"]:
            overlaps.append((previous, current))

    print()
    print("=== Layout analysis ===")

    if overlaps:
        print(f"Overlapping streams: {len(overlaps)}")

        for previous, current in overlaps[:10]:
            print(
                f"  {format_offset(previous['offset'])} -> "
                f"{format_offset(previous['end'])}"
            )
            print(
                f"  overlaps with "
                f"{format_offset(current['offset'])}"
            )
    else:
        print("Overlapping streams: 0")

    # Check gaps between consecutive streams.
    gaps = []

    for previous, current in zip(streams, streams[1:]):
        if current["offset"] > previous["end"]:
            gaps.append({
                "start": previous["end"],
                "end": current["offset"],
                "size": current["offset"] - previous["end"],
            })

    print(f"Gaps between streams: {len(gaps)}")

    if gaps:
        print()
        print("First 20 gaps:")

        for gap in gaps[:20]:
            print(
                f"  {format_offset(gap['start'])} -> "
                f"{format_offset(gap['end'])} "
                f"({format_size(gap['size'])} bytes)"
            )

    covered = sum(stream["compressed_size"] for stream in streams)

    print()
    print(f"File size:          {format_size(len(data))} bytes")
    print(f"Stream data total:  {format_size(covered)} bytes")

    return streams

def inspect_stream_content(data: bytes, streams):
    print()
    print("=== Stream content samples ===")

    sample_indices = [
        0,
        1,
        2,
        3,
        9,
        99,
        499,
        999,
        len(streams) - 1,
    ]

    seen = set()

    for index in sample_indices:
        if index < 0 or index >= len(streams) or index in seen:
            continue

        seen.add(index)

        stream = streams[index]

        compressed = data[
            stream["offset"]:stream["end"]
        ]

        try:
            decompressed = zlib.decompress(compressed)
        except zlib.error:
            continue

        print()
        print(
            f"Stream #{index + 1} "
            f"@ {format_offset(stream['offset'])}"
        )

        print(
            f"  Compressed:   "
            f"{format_size(len(compressed))} bytes"
        )

        print(
            f"  Decompressed: "
            f"{format_size(len(decompressed))} bytes"
        )

        print("  First 32 bytes:")

        print(
            "   ",
            " ".join(
                f"{b:02X}"
                for b in decompressed[:32]
            )
        )

        try:
            text = decompressed.decode("utf-8")

            preview = text[:300]

            preview = (
                preview
                .replace("\r", "\\r")
                .replace("\n", "\\n")
            )

            print("  UTF-8:")
            print(f"    {preview}")

        except UnicodeDecodeError:
            print("  UTF-8: not valid UTF-8")

def main():
    parser = argparse.ArgumentParser(
        description="Inspect School Days HQ resource files."
    )

    parser.add_argument(
        "file",
        help="File to inspect"
    )

    args = parser.parse_args()

    path = Path(args.file)

    if not path.exists():
        print(f"ERROR: File does not exist: {path}")
        return 1

    if not path.is_file():
        print(f"ERROR: Not a file: {path}")
        return 1

    data = path.read_bytes()

    print()
    print("=" * 70)
    print(" School Days HQ Resource Inspector")
    print("=" * 70)

    print()
    print(f"File: {path}")
    print(f"Size: {format_size(len(data))} bytes")
    print(f"Header: {' '.join(f'{b:02X}' for b in data[:16])}")

    streams = inspect_zlib(data)
    inspect_zlib(data)
    inspect_stream_content(data, streams)
    inspect_tail(data, streams)
    inspect_jpeg(data)

    print()
    print("=" * 70)
    print("Inspection finished.")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())