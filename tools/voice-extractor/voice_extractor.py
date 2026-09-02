from pathlib import Path
import argparse
import struct


def find_ogg_streams(data: bytes):
    positions = []
    start = 0

    while True:
        pos = data.find(b"OggS", start)

        if pos == -1:
            break

        positions.append(pos)
        start = pos + 4

    return positions


def get_ogg_page_size(data: bytes, offset: int):
    if data[offset:offset + 4] != b"OggS":
        return None

    if offset + 27 > len(data):
        return None

    segment_count = data[offset + 26]

    header_size = 27 + segment_count

    if offset + header_size > len(data):
        return None

    body_size = sum(
        data[offset + 27:offset + 27 + segment_count]
    )

    return header_size + body_size


def extract_stream(data: bytes, start: int, limit: int):
    pos = start
    pages = 0

    while pos < limit:
        if data[pos:pos + 4] != b"OggS":
            break

        page_size = get_ogg_page_size(data, pos)

        if page_size is None:
            break

        pos += page_size
        pages += 1

        if pos >= limit:
            break

        # El siguiente OggS marca el comienzo de otro stream.
        if data[pos:pos + 4] == b"OggS":
            continue

        break

    return pos, pages


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True)

    args = parser.parse_args()

    data = args.input.read_bytes()

    print("=" * 70)
    print(" School Days HQ Voice Extractor")
    print("=" * 70)
    print()
    print(f"Input:  {args.input}")
    print(f"Size:   {len(data):,} bytes")
    print()

    pe_offset = struct.unpack_from("<I", data, 0x3C)[0]
    section_count = struct.unpack_from("<H", data, pe_offset + 6)[0]
    optional_size = struct.unpack_from("<H", data, pe_offset + 20)[0]

    section_table = pe_offset + 24 + optional_size

    pe_end = 0

    for i in range(section_count):
        off = section_table + i * 40

        raw_size = struct.unpack_from("<I", data, off + 16)[0]
        raw_pointer = struct.unpack_from("<I", data, off + 20)[0]

        pe_end = max(
            pe_end,
            raw_pointer + raw_size
        )

    overlay = data[pe_end:]

    positions = find_ogg_streams(overlay)

    print(f"PE end:          0x{pe_end:X}")
    print(f"OggS signatures: {len(positions)}")
    print()

    args.output.mkdir(
        parents=True,
        exist_ok=True
    )

    extracted = 0
    total_bytes = 0

    for index, relative_start in enumerate(positions):
        start = pe_end + relative_start

        if index + 1 < len(positions):
            next_start = pe_end + positions[index + 1]
        else:
            next_start = len(data)

        end, pages = extract_stream(
            data,
            start,
            next_start
        )

        if end <= start:
            continue

        output = args.output / f"{extracted:04d}.ogg"

        output.write_bytes(
            data[start:end]
        )

        size = end - start

        extracted += 1
        total_bytes += size

        print(
            f"[{extracted:04d}] "
            f"0x{start:08X} -> 0x{end:08X} "
            f"{size:,} bytes "
            f"({pages} pages)"
        )

    print()
    print("=" * 70)
    print(f"Extracted: {extracted}")
    print(f"Total:     {total_bytes:,} bytes")
    print(f"Output:    {args.output}")
    print("=" * 70)


if __name__ == "__main__":
    main()