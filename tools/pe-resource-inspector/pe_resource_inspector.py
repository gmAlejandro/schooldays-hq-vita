from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path


def u16(data: bytes, offset: int) -> int:
    return struct.unpack_from("<H", data, offset)[0]


def u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def read_c_string(data: bytes, offset: int) -> str:
    end = data.find(b"\x00", offset)
    if end == -1:
        end = len(data)
    return data[offset:end].decode("ascii", errors="replace")


def rva_to_offset(rva: int, sections: list[dict]) -> int | None:
    for section in sections:
        start = section["virtual_address"]
        size = max(section["virtual_size"], section["raw_size"])

        if start <= rva < start + size:
            return section["raw_pointer"] + (rva - start)

    return None


def parse_pe(data: bytes) -> dict:
    if data[:2] != b"MZ":
        raise ValueError("No es un ejecutable PE: falta MZ")

    pe_offset = u32(data, 0x3C)

    if data[pe_offset:pe_offset + 4] != b"PE\x00\x00":
        raise ValueError(f"Firma PE inválida en 0x{pe_offset:X}")

    coff = pe_offset + 4

    machine = u16(data, coff)
    section_count = u16(data, coff + 2)
    optional_size = u16(data, coff + 16)

    optional = coff + 20

    magic = u16(data, optional)

    if magic == 0x10B:
        is_64 = False
        data_directory_offset = optional + 96
    elif magic == 0x20B:
        is_64 = True
        data_directory_offset = optional + 112
    else:
        raise ValueError(f"Optional header desconocido: 0x{magic:X}")

    number_of_rva_sizes = u32(data, data_directory_offset - 4)

    resource_rva = None
    resource_size = None

    if number_of_rva_sizes > 2:
        resource_rva = u32(data, data_directory_offset + 8 * 2)
        resource_size = u32(data, data_directory_offset + 8 * 2 + 4)

    section_table = optional + optional_size

    sections = []

    for i in range(section_count):
        off = section_table + i * 40

        name = data[off:off + 8].split(b"\x00", 1)[0].decode(
            "ascii", errors="replace"
        )

        virtual_size = u32(data, off + 8)
        virtual_address = u32(data, off + 12)
        raw_size = u32(data, off + 16)
        raw_pointer = u32(data, off + 20)

        sections.append({
            "name": name,
            "virtual_size": virtual_size,
            "virtual_address": virtual_address,
            "raw_size": raw_size,
            "raw_pointer": raw_pointer,
        })

    return {
        "pe_offset": pe_offset,
        "machine": f"0x{machine:04X}",
        "architecture": "x64" if is_64 else "x86",
        "section_count": section_count,
        "resource_rva": resource_rva,
        "resource_size": resource_size,
        "sections": sections,
    }


def inspect_resources(data: bytes, pe: dict) -> list[dict]:
    rva = pe["resource_rva"]

    if not rva:
        return []

    root_offset = rva_to_offset(rva, pe["sections"])

    if root_offset is None:
        raise ValueError("No se pudo convertir Resource RVA a offset")

    results = []

    def walk(directory_offset: int, level: int, path: list[str]):
        if level > 3:
            return

        characteristics = u32(data, directory_offset)
        timestamp = u32(data, directory_offset + 4)
        major = u16(data, directory_offset + 8)
        minor = u16(data, directory_offset + 10)
        named_count = u16(data, directory_offset + 12)
        id_count = u16(data, directory_offset + 14)

        total = named_count + id_count
        entries_offset = directory_offset + 16

        for i in range(total):
            entry = entries_offset + i * 8

            name_or_id = u32(data, entry)
            offset_to_data = u32(data, entry + 4)

            is_named = bool(name_or_id & 0x80000000)

            if is_named:
                name_offset = rva_to_offset(
                    rva + (name_or_id & 0x7FFFFFFF),
                    pe["sections"],
                )

                if name_offset is not None:
                    name_length = u16(data, name_offset)
                    raw_name = data[
                        name_offset + 2:
                        name_offset + 2 + name_length * 2
                    ]

                    name = raw_name.decode(
                        "utf-16le",
                        errors="replace",
                    )
                else:
                    name = "<invalid-name>"
            else:
                name = str(name_or_id & 0xFFFF)

            child_name = name
            child_path = path + [child_name]

            is_directory = bool(offset_to_data & 0x80000000)

            if is_directory:
                child_rva = rva + (offset_to_data & 0x7FFFFFFF)
                child_offset = rva_to_offset(
                    child_rva,
                    pe["sections"],
                )

                if child_offset is not None:
                    walk(
                        child_offset,
                        level + 1,
                        child_path,
                    )

            else:
                data_rva = rva + offset_to_data
                data_entry_offset = rva_to_offset(
                    data_rva,
                    pe["sections"],
                )

                if data_entry_offset is None:
                    continue

                resource_data_rva = u32(data, data_entry_offset)
                resource_size_value = u32(
                    data,
                    data_entry_offset + 4,
                )
                codepage = u32(
                    data,
                    data_entry_offset + 8,
                )

                raw_offset = rva_to_offset(
                    resource_data_rva,
                    pe["sections"],
                )

                item = {
                    "path": child_path,
                    "rva": f"0x{resource_data_rva:X}",
                    "offset": (
                        f"0x{raw_offset:X}"
                        if raw_offset is not None
                        else None
                    ),
                    "size": resource_size_value,
                    "codepage": codepage,
                }

                if raw_offset is not None:
                    preview = data[
                        raw_offset:
                        raw_offset + min(resource_size_value, 32)
                    ]

                    item["header"] = preview.hex(" ").upper()

                results.append(item)

    walk(root_offset, 0, [])

    return results


def main() -> int:
    parser = argparse.ArgumentParser(
        description="School Days HQ PE resource inspector"
    )

    parser.add_argument("input", type=Path)
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
    )

    args = parser.parse_args()

    data = args.input.read_bytes()

    print("=" * 70)
    print(" School Days HQ PE Resource Inspector")
    print("=" * 70)
    print()
    print(f"File: {args.input}")
    print(f"Size: {len(data):,} bytes")
    print()

    pe = parse_pe(data)

    print("=== PE ===")
    print(f"PE offset:       0x{pe['pe_offset']:X}")
    print(f"Architecture:    {pe['architecture']}")
    print(f"Machine:         {pe['machine']}")
    print(f"Sections:        {pe['section_count']}")
    print()

    print("=== Sections ===")

    for section in pe["sections"]:
        print(
            f"{section['name']:<10} "
            f"RVA 0x{section['virtual_address']:08X} "
            f"Raw 0x{section['raw_pointer']:08X} "
            f"Size {section['raw_size']:,}"
        )

    print()

    print("=== Resources ===")

    resources = inspect_resources(data, pe)

    print(f"Resource entries: {len(resources)}")
    print()

    for index, resource in enumerate(resources, 1):
        print(
            f"[{index:04d}] "
            f"{'/'.join(resource['path'])} "
            f"-> offset {resource['offset']} "
            f"size {resource['size']:,}"
        )

        if resource.get("header"):
            print(
                f"       {resource['header']}"
            )

    result = {
        "file": str(args.input),
        "size": len(data),
        "pe": pe,
        "resources": resources,
    }

    if args.output:
        args.output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        args.output.write_text(
            json.dumps(
                result,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        print()
        print(f"Report: {args.output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())