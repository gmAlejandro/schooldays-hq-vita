from pathlib import Path
import struct
import zlib
import sys


def ogg_crc(data):
    crc = 0
    for byte in data:
        crc ^= byte << 24
        for _ in range(8):
            if crc & 0x80000000:
                crc = ((crc << 1) ^ 0x04C11DB7) & 0xFFFFFFFF
            else:
                crc = (crc << 1) & 0xFFFFFFFF
    return crc


def parse_page(data, pos):
    if data[pos:pos + 4] != b"OggS":
        return None

    if pos + 27 > len(data):
        return None

    page_segments = data[pos + 26]

    end_header = pos + 27 + page_segments
    if end_header > len(data):
        return None

    body_size = sum(data[pos + 27:end_header])
    end = end_header + body_size

    if end > len(data):
        return None

    return {
        "pos": pos,
        "end": end,
        "raw": data[pos:end],
        "type": data[pos + 5],
        "serial": struct.unpack_from("<I", data, pos + 14)[0],
        "seq": struct.unpack_from("<I", data, pos + 18)[0],
    }


def make_bos_page(serial, packet):
    if len(packet) > 255:
        raise ValueError("Identification packet demasiado grande")

    # Ogg page header:
    # capture, version, type(BOS), granule, serial, seq, crc, segments
    header = bytearray(27)
    header[0:4] = b"OggS"
    header[4] = 0
    header[5] = 0x02          # BOS
    header[6:14] = b"\x00" * 8
    struct.pack_into("<I", header, 14, serial)
    struct.pack_into("<I", header, 18, 0)
    header[22:26] = b"\x00" * 4
    header[26] = 1

    page = header + bytes([len(packet)]) + packet

    crc = ogg_crc(page)
    struct.pack_into("<I", page, 22, crc)

    return bytes(page)


def find_identification_before(data, ogg_pos, serial):
    """
    Busca hacia atrás el paquete Vorbis identification (01vorbis)
    correspondiente al stream.
    """

    # Buscamos el último 01vorbis antes de la primera página OggS.
    marker = b"\x01vorbis"

    start = max(0, ogg_pos - 512)

    positions = []
    p = start

    while True:
        p = data.find(marker, p, ogg_pos)
        if p < 0:
            break
        positions.append(p)
        p += 1

    if not positions:
        return None

    # El identification packet Vorbis estándar mide 30 bytes.
    p = positions[-1]

    packet = data[p:p + 30]

    if len(packet) != 30:
        return None

    if packet[:7] != b"\x01vorbis":
        return None

    return packet


def main():
    if len(sys.argv) != 3:
        print("Uso:")
        print("python tools\\voice-mapper\\ogg_rebuild_full.py GPK OUTPUT")
        sys.exit(1)

    gpk_path = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])

    data = gpk_path.read_bytes()
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print(" School Days HQ FULL OGG Rebuilder")
    print("=" * 70)
    print()
    print(f"GPK: {len(data):,} bytes")

    # Localizar todas las páginas OggS.
    pages = []
    pos = 0

    while True:
        pos = data.find(b"OggS", pos)

        if pos < 0:
            break

        page = parse_page(data, pos)

        if page is None:
            pos += 4
            continue

        pages.append(page)
        pos = page["end"]

    print(f"Pages: {len(pages):,}")

    # Agrupar páginas por serial.
    streams = {}

    for page in pages:
        streams.setdefault(page["serial"], []).append(page)

    print(f"Streams: {len(streams):,}")
    print()

    ok = 0
    fail = 0

    for index, (serial, stream_pages) in enumerate(streams.items()):

        stream_pages.sort(key=lambda x: x["seq"])

        first_pos = stream_pages[0]["pos"]

        identification = find_identification_before(
            data,
            first_pos,
            serial
        )

        if identification is None:
            print(f"[FAIL] {index:04d} serial=0x{serial:08X} sin 01vorbis")
            fail += 1
            continue

        # Construimos el OGG completo:
        # 1. Identification packet (BOS)
        # 2. Todas las páginas existentes del stream
        result = bytearray()

        result.extend(
            make_bos_page(serial, identification)
        )

        for page in stream_pages:
            result.extend(page["raw"])

        out = output_dir / f"{index:04d}.ogg"
        out.write_bytes(result)

        ok += 1

        if index < 20:
            print(
                f"{index:04d}.ogg "
                f"serial=0x{serial:08X} "
                f"pages={len(stream_pages):3d} "
                f"size={len(result):7d} "
                f"ID=OK"
            )

    print()
    print("=" * 70)
    print("Resultado")
    print("=" * 70)
    print(f"OK:   {ok}")
    print(f"FAIL: {fail}")
    print(f"Total: {len(streams)}")
    print()
    print(f"Salida: {output_dir}")


if __name__ == "__main__":
    main()