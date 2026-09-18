from pathlib import Path

path = Path(r"Original\SCHOOLDAYS HQ\Packs\Voice00.GPK")
data = path.read_bytes()

signatures = {
    b"\x01vorbis": "IDENTIFICATION",
    b"\x03vorbis": "COMMENT",
    b"\x05vorbis": "SETUP",
}

for signature, name in signatures.items():
    positions = []
    start = 0

    while True:
        pos = data.find(signature, start)

        if pos == -1:
            break

        positions.append(pos)
        start = pos + 1

    print()
    print(f"{name}: {len(positions)}")

    for pos in positions[:50]:
        print(f"  0x{pos:08X} ({pos})")

    if len(positions) > 50:
        print(f"  ... {len(positions) - 50} más")