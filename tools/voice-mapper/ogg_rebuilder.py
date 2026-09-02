from pathlib import Path
import argparse
import struct

def read_page(data):
    if len(data) < 27 or data[:4] != b"OggS":
        return None

    header_type = data[5]
    serial = struct.unpack_from("<I", data, 14)[0]
    sequence = struct.unpack_from("<I", data, 18)[0]
    page_segments = data[26]

    if len(data) < 27 + page_segments:
        return None

    sizes = data[27:27 + page_segments]
    page_size = 27 + page_segments + sum(sizes)

    if len(data) < page_size:
        return None

    return {
        "type": header_type,
        "serial": serial,
        "sequence": sequence,
        "size": page_size,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_dir")
    parser.add_argument("-o", "--output", required=True)
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    pages = []

    for path in sorted(input_dir.glob("*.ogg")):
        data = path.read_bytes()
        info = read_page(data)

        if info is None:
            print(f"SKIP {path.name}: invalid Ogg page")
            continue

        pages.append((path, data, info))

    streams = {}

    for path, data, info in pages:
        streams.setdefault(info["serial"], []).append((path, data, info))

    print("=" * 70)
    print(" School Days HQ OGG Rebuilder")
    print("=" * 70)
    print()
    print(f"Pages:   {len(pages)}")
    print(f"Streams: {len(streams)}")
    print()

    rebuilt = 0

    for index, (serial, stream_pages) in enumerate(streams.items()):
        stream_pages.sort(key=lambda x: x[2]["sequence"])

        expected = 1
        valid_order = True

        for _, _, info in stream_pages:
            if info["sequence"] != expected:
                valid_order = False
                break
            expected += 1

        output = output_dir / f"{index:04d}.ogg"

        with output.open("wb") as f:
            for _, data, _ in stream_pages:
                f.write(data)

        has_eos = bool(stream_pages[-1][2]["type"] & 0x04)
        has_bos = bool(stream_pages[0][2]["type"] & 0x02)

        print(
            f"{index:04d}.ogg  "
            f"serial=0x{serial:08X}  "
            f"pages={len(stream_pages):3d}  "
            f"size={output.stat().st_size:7d}  "
            f"BOS={has_bos} EOS={has_eos} ORDER={valid_order}"
        )

        rebuilt += 1

    print()
    print("=" * 70)
    print(f"Rebuilt: {rebuilt}")
    print(f"Output:  {output_dir}")
    print("=" * 70)


if __name__ == "__main__":
    main()
