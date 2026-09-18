from pathlib import Path
from collections import defaultdict
import struct

ROOT = Path("research/voice/extracted")

VORBIS_HEADERS = {
    b"\x01vorbis": "IDENTIFICATION",
    b"\x03vorbis": "COMMENT",
    b"\x05vorbis": "SETUP",
}


def parse_page(data):
    if len(data) < 27 or data[:4] != b"OggS":
        raise ValueError("Página Ogg inválida")

    flags = data[5]
    serial = struct.unpack_from("<I", data, 14)[0]
    sequence = struct.unpack_from("<I", data, 18)[0]
    granule = struct.unpack_from("<Q", data, 6)[0]

    segment_count = data[26]
    lacing = data[27:27 + segment_count]

    body_start = 27 + segment_count
    body_size = sum(lacing)
    body = data[body_start:body_start + body_size]

    return {
        "flags": flags,
        "serial": serial,
        "sequence": sequence,
        "granule": granule,
        "lacing": lacing,
        "body": body,
    }


def rebuild_packets(pages):
    packets = []
    current = bytearray()

    for page in pages:
        pos = 0

        for lace in page["lacing"]:
            current.extend(page["body"][pos:pos + lace])
            pos += lace

            if lace < 255:
                packets.append(bytes(current))
                current.clear()

    if current:
        packets.append(bytes(current))

    return packets


def describe_packet(packet):
    for signature, name in VORBIS_HEADERS.items():
        if packet.startswith(signature):
            return name

    if not packet:
        return "EMPTY"

    # Vorbis audio packets have bit 0 = 0.
    if (packet[0] & 1) == 0:
        return "AUDIO"

    return "UNKNOWN"


def main():
    files = sorted(ROOT.glob("*.ogg"))

    print(f"Physical pages: {len(files)}")

    streams = defaultdict(list)

    for path in files:
        try:
            page = parse_page(path.read_bytes())
            streams[page["serial"]].append(page)
        except Exception as e:
            print(f"[ERROR] {path.name}: {e}")

    print(f"Logical streams: {len(streams)}")
    print()

    total_packets = 0
    vorbis_header_counts = defaultdict(int)

    for index, (serial, pages) in enumerate(sorted(streams.items()), 1):
        pages.sort(key=lambda p: p["sequence"])

        packets = rebuild_packets(pages)
        total_packets += len(packets)

        first = pages[0]
        last = pages[-1]

        bos = bool(first["flags"] & 0x02)
        eos = bool(last["flags"] & 0x04)

        types = [describe_packet(p) for p in packets]

        for t in types:
            if t in VORBIS_HEADERS:
                vorbis_header_counts[t] += 1

        print(
            f"[{index:03d}/{len(streams):03d}] "
            f"serial=0x{serial:08X} "
            f"pages={len(pages):3d} "
            f"packets={len(packets):3d} "
            f"BOS={bos} EOS={eos}"
        )

        for pindex, packet in enumerate(packets[:6]):
            preview = packet[:16].hex(" ")
            kind = describe_packet(packet)

            print(
                f"    packet {pindex:02d}: "
                f"{kind:14s} "
                f"size={len(packet):6d} "
                f"head={preview}"
            )

        print()

    print("========== SUMMARY ==========")
    print(f"Streams:  {len(streams)}")
    print(f"Packets:  {total_packets}")
    print()
    print("Vorbis headers detected:")
    print(f"  Identification: {vorbis_header_counts['IDENTIFICATION']}")
    print(f"  Comment:        {vorbis_header_counts['COMMENT']}")
    print(f"  Setup:          {vorbis_header_counts['SETUP']}")


if __name__ == "__main__":
    main()