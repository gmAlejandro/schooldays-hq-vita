from pathlib import Path
import argparse
import json
import struct


MAGICS = {
    b"OggS": "ogg",
    b"RIFF": "riff",
    b"FORM": "form",
    b"ID3": "mp3/id3",
    b"\xFF\xFB": "mp3",
    b"\xFF\xF3": "mp3",
    b"\xFF\xF2": "mp3",
    b"fLaC": "flac",
    b"VAGp": "vag",
    b"RIFF": "riff",
    b"AC-3": "ac3",
}


def find_all(data, needle):
    result = []
    start = 0

    while True:
        pos = data.find(needle, start)

        if pos == -1:
            break

        result.append(pos)
        start = pos + 1

    return result


def scan_ascii(data):
    strings = []
    current = bytearray()
    start = 0

    for i, byte in enumerate(data):
        if 32 <= byte <= 126:
            if not current:
                start = i
            current.append(byte)
        else:
            if len(current) >= 6:
                strings.append({
                    "offset": start,
                    "text": current.decode("ascii", errors="replace")
                })

            current.clear()

    if len(current) >= 6:
        strings.append({
            "offset": start,
            "text": current.decode("ascii", errors="replace")
        })

    return strings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("-o", "--output", type=Path)

    args = parser.parse_args()

    data = args.input.read_bytes()

    print("=" * 70)
    print(" School Days HQ Voice Container Inspector")
    print("=" * 70)
    print()
    print(f"File: {args.input}")
    print(f"Size: {len(data):,} bytes")
    print()

    pe_offset = struct.unpack_from("<I", data, 0x3C)[0]

    # El PE de Voice00 termina aproximadamente después de las secciones.
    # Buscamos el comienzo de la zona que no pertenece al PE.
    number_of_sections = struct.unpack_from("<H", data, pe_offset + 6)[0]
    optional_size = struct.unpack_from("<H", data, pe_offset + 20)[0]

    section_table = pe_offset + 24 + optional_size

    sections = []

    for i in range(number_of_sections):
        off = section_table + i * 40

        name = data[off:off + 8].split(b"\0", 1)[0].decode(
            "ascii", errors="replace"
        )

        raw_size = struct.unpack_from("<I", data, off + 16)[0]
        raw_pointer = struct.unpack_from("<I", data, off + 20)[0]

        sections.append({
            "name": name,
            "offset": raw_pointer,
            "size": raw_size,
            "end": raw_pointer + raw_size,
        })

    pe_end = max(section["end"] for section in sections)

    print("=== PE sections ===")

    for section in sections:
        print(
            f"{section['name']:<8} "
            f"0x{section['offset']:08X} -> "
            f"0x{section['end']:08X} "
            f"({section['size']:,} bytes)"
        )

    print()
    print(f"PE data end:  0x{pe_end:X}")
    print(f"Overlay:      0x{pe_end:X}")
    print(f"Overlay size: {len(data) - pe_end:,} bytes")
    print()

    overlay = data[pe_end:]

    print("=== Known audio signatures ===")

    signatures = {}

    for magic, name in MAGICS.items():
        positions = find_all(overlay, magic)

        if positions:
            signatures[name] = positions

            print(
                f"{name:<10} {len(positions):>6} "
                f"first: 0x{positions[0] + pe_end:X}"
            )

    if not signatures:
        print("No known audio signatures found.")

    print()
    print("=== Interesting strings in overlay ===")

    strings = scan_ascii(overlay)

    interesting = []

    keywords = (
        "voice",
        "wav",
        "ogg",
        "mp3",
        "sound",
        "audio",
        "00-",
        "Voice00",
        ".dat",
        ".bin",
    )

    for item in strings:
        text = item["text"]

        if any(keyword.lower() in text.lower() for keyword in keywords):
            item = {
                "offset": item["offset"] + pe_end,
                "text": text
            }

            interesting.append(item)

            print(
                f"0x{item['offset']:08X}  {item['text'][:160]}"
            )

    print()
    print("=== Overlay first 256 bytes ===")
    print(overlay[:256].hex(" "))

    result = {
        "file": str(args.input),
        "size": len(data),
        "pe_end": pe_end,
        "overlay_size": len(overlay),
        "sections": sections,
        "signatures": {
            name: [
                position + pe_end
                for position in positions
            ]
            for name, positions in signatures.items()
        },
        "interesting_strings": interesting,
    }

    if args.output:
        args.output.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        args.output.write_text(
            json.dumps(
                result,
                indent=2,
                ensure_ascii=False
            ),
            encoding="utf-8"
        )

        print()
        print(f"Report: {args.output}")


if __name__ == "__main__":
    main()