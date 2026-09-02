from pathlib import Path
import argparse
import struct

POLY = 0x04C11DB7

def make_crc_table():
    table = []
    for i in range(256):
        r = i << 24
        for _ in range(8):
            r = ((r << 1) ^ POLY) & 0xFFFFFFFF if r & 0x80000000 else (r << 1) & 0xFFFFFFFF
        table.append(r)
    return table

CRC_TABLE = make_crc_table()

def ogg_crc(data):
    crc = 0
    for b in data:
        crc = ((crc << 8) & 0xFFFFFFFF) ^ CRC_TABLE[((crc >> 24) ^ b) & 0xFF]
    return crc

def split_pages(data):
    pages, pos = [], 0
    while pos < len(data):
        if data[pos:pos+4] != b"OggS":
            raise ValueError(f"OggS no encontrado en 0x{pos:X}")
        if len(data) - pos < 27:
            raise ValueError("Cabecera incompleta")
        n = data[pos+26]
        h = 27 + n
        if pos + h > len(data):
            raise ValueError("Tabla de segmentos incompleta")
        size = h + sum(data[pos+27:pos+h])
        if pos + size > len(data):
            raise ValueError("Página truncada")
        pages.append(bytearray(data[pos:pos+size]))
        pos += size
    return pages

def repair_stream(data):
    pages = split_pages(data)
    for i, page in enumerate(pages):
        if i == 0:
            page[5] |= 0x02
        else:
            page[5] &= ~0x02
        if i == len(pages)-1:
            page[5] |= 0x04
        page[22:26] = b"\x00"*4
        struct.pack_into("<I", page, 22, ogg_crc(page))
    return b"".join(pages), len(pages)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("input_dir")
    ap.add_argument("-o","--output",required=True)
    a=ap.parse_args()
    src,dst=Path(a.input_dir),Path(a.output)
    dst.mkdir(parents=True,exist_ok=True)
    files=sorted(src.glob("*.ogg"))
    ok=fail=0
    print("="*70); print(" School Days HQ OGG Repair"); print("="*70)
    print(f"Entrada: {src}\nSalida:  {dst}\nArchivos: {len(files)}\n")
    for i,f in enumerate(files,1):
        try:
            repaired,pages=repair_stream(f.read_bytes())
            (dst/f.name).write_bytes(repaired); ok+=1
            if i%25==0 or i==len(files): print(f"[{i}/{len(files)}] OK={ok} FAIL={fail}")
        except Exception as e:
            fail+=1; print(f"[FAIL] {f.name}: {e}")
    print(f"\nOK: {ok}\nFAIL: {fail}\nTotal: {len(files)}\nSalida: {dst}")

if __name__=="__main__": main()
