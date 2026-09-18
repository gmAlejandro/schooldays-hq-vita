from pathlib import Path
import struct
import sys


def parse_pages(data):
    pages = []
    pos = 0

    while True:
        pos = data.find(b"OggS", pos)
        if pos < 0:
            break

        if pos + 27 > len(data):
            break

        version = data[pos + 4]
        header_type = data[pos + 5]
        serial = struct.unpack_from("<I", data, pos + 14)[0]
        sequence = struct.unpack_from("<I", data, pos + 18)[0]
        segment_count = data[pos + 26]

        if pos + 27 + segment_count > len(data):
            pos += 4
            continue

        lacing = data[pos + 27:pos + 27 + segment_count]
        payload_size = sum(lacing)
        page_size = 27 + segment_count + payload_size

        if pos + page_size > len(data):
            pos += 4
            continue

        pages.append({
            "offset": pos,
            "serial": serial,
            "sequence": sequence,
            "header_type": header_type,
            "lacing": lacing,
            "data": data[pos:pos + page_size],
        })

        pos += page_size

    return pages


def main():
    if len(sys.argv) != 3:
        print(
            "Uso: python ogg_stream_extractor.py "
            '"Voice00.GPK" "salida"'
        )
        sys.exit(1)

    source = Path(sys.argv[1])
    output = Path(sys.argv[2])
    output.mkdir(parents=True, exist_ok=True)

    data = source.read_bytes()

    print("=" * 70)
    print(" School Days HQ OGG Stream Extractor")
    print("=" * 70)
    print()
    print(f"GPK:   {len(data):,} bytes")

    pages = parse_pages(data)

    print(f"Pages: {len(pages):,}")

    streams = {}

    for page in pages:
        streams.setdefault(page["serial"], []).append(page)

    print(f"Streams: {len(streams):,}")
    print()

    # Ordenar páginas de cada stream
    for serial in streams:
        streams[serial].sort(key=lambda p: p["sequence"])

    # Mostrar los primeros streams y localizar las cabeceras Vorbis
    print("Primeros streams:")
    print()

    for i, (serial, stream_pages) in enumerate(streams.items()):
        blob = b"".join(p["data"] for p in stream_pages)

        p01 = blob.find(b"\x01vorbis")
        p03 = blob.find(b"\x03vorbis")
        p05 = blob.find(b"\x05vorbis")

        print(
            f"{i:03d} serial=0x{serial:08X} "
            f"pages={len(stream_pages):3d} "
            f"01={p01:6d} "
            f"03={p03:6d} "
            f"05={p05:6d}"
        )

        if i >= 19:
            break

    print()
    print("No se han escrito archivos todavía.")


if __name__ == "__main__":
    main()