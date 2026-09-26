#!/usr/bin/env python3
"""Audit bounded startup/integrity evidence in exact E5000 D images.

This read-only checker does not dump vendor bytes. It verifies the raw header,
startup calls, two runtime-initializer records, whole-image literal searches,
and structured tail of exact D4.1/D4.3/D4.5 samples listed in ASSETS.md. It
cannot inspect the resident motor bootloader or prove that a modified image
will boot.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path


LOAD_BASE = 0x10000
SIZE_FIELD = LOAD_BASE + 0x18

PROFILES = {
    "fdb0f40b94d55ce9d098f803fe0f2f4038a3ce3343fe539bf151a9511dda14ec": {
        "version": "D4.1.0", "size": 135_052, "entry": 0x2EBB8,
        "entry_call": 0x2EBC6, "runtime": 0x30B20, "main_call": 0x30B32,
        "main": 0x2B076, "table": 0x30BC8, "zero": 0x30B8C,
        "zero_length": 0x2520, "zero_start": 0x200008B0,
        "copy": 0x29B3A, "copy_source": 0x73C,
        "tail": "ffff80012201020201ff0000ffff6574",
    },
    "3d3df4dfe3de333062f445b6719fa5033f93dc9d384448134ee6041d216c6af0": {
        "version": "D4.3.0", "size": 132_072, "entry": 0x2E214,
        "entry_call": 0x2E222, "runtime": 0x2FF20, "main_call": 0x2FF36,
        "main": 0x2A9BE, "table": 0x2FFCC, "zero": 0x2FF90,
        "zero_length": 0x2530, "zero_start": 0x20000490,
        "copy": 0x294AA, "copy_source": 0x7EA,
        "tail": "ff80012201020201ff000000ffff6574",
    },
    "44806bd54aedff95a88bb73fafe0f0581297f2f67b2ea35545cea012899d90bb": {
        "version": "D4.5.0", "size": 138_072, "entry": 0x2F984,
        "entry_call": 0x2F992, "runtime": 0x31690, "main_call": 0x316A6,
        "main": 0x2C0B2, "table": 0x3173C, "zero": 0x31700,
        "zero_length": 0x25D0, "zero_start": 0x20000490,
        "copy": 0x2C33A, "copy_source": 0x7EA,
        "tail": "ff80012201020201ff000000ffff6574",
    },
}


def offset(address):
    return address - LOAD_BASE


def locations(data, needle):
    found, start = [], 0
    while True:
        position = data.find(needle, start)
        if position < 0:
            return found
        found.append(position)
        start = position + 1


def thumb_bl_target(data, address):
    first, second = struct.unpack_from("<HH", data, offset(address))
    if first & 0xF800 != 0xF000 or second & 0xD000 != 0xD000:
        raise ValueError(f"expected Thumb BL at 0x{address:x}")
    sign, imm10 = (first >> 10) & 1, first & 0x03FF
    j1, j2, imm11 = (second >> 13) & 1, (second >> 11) & 1, second & 0x07FF
    i1, i2 = 1 ^ (j1 ^ sign), 1 ^ (j2 ^ sign)
    immediate = ((sign << 24) | (i1 << 23) | (i2 << 22) |
                 (imm10 << 12) | (imm11 << 1))
    if sign:
        immediate -= 1 << 25
    return address + 4 + immediate


def initializer_record(data, table, record_offset):
    relative, length, source, destination = struct.unpack_from(
        "<iIII", data, offset(table + record_offset)
    )
    return {
        "target": (table + record_offset + relative) & ~1,
        "length": length,
        "source": source,
        "destination": destination,
    }


def inspect(data, source):
    digest = hashlib.sha256(data).hexdigest()
    profile = PROFILES.get(digest)
    if profile is None or len(data) != profile["size"]:
        raise ValueError(f"{source}: not an exact recorded D4.1/D4.3/D4.5 raw image")
    if data[:16] != b"\xff" * 16:
        raise ValueError("raw header prefix mismatch")
    entry_pointer, declared_size = struct.unpack_from("<II", data, 0x14)
    if entry_pointer != profile["entry"] | 1 or declared_size != len(data):
        raise ValueError("raw entry pointer or declared image size mismatch")
    if thumb_bl_target(data, profile["entry_call"]) != profile["runtime"]:
        raise ValueError("entry-to-runtime call mismatch")
    if thumb_bl_target(data, profile["main_call"]) != profile["main"]:
        raise ValueError("runtime-to-main call mismatch")
    zero = initializer_record(data, profile["table"], 0)
    copy = initializer_record(data, profile["table"], 16)
    if zero != {"target": profile["zero"], "length": profile["zero_length"],
               "source": profile["zero_start"], "destination": 0}:
        raise ValueError("RAM-zero initializer record mismatch")
    if copy != {"target": profile["copy"], "length": 12,
               "source": profile["copy_source"], "destination": 0x2000000C}:
        raise ValueError("ROM-to-RAM initializer record mismatch")
    if not data.endswith(bytes.fromhex(profile["tail"])):
        raise ValueError("structured image tail mismatch")
    size_bytes = struct.pack("<I", declared_size)
    end_address = LOAD_BASE + declared_size
    size_occurrences = locations(data, size_bytes)
    end_occurrences = locations(data, struct.pack("<I", end_address))
    field_pointer_occurrences = locations(data, struct.pack("<I", SIZE_FIELD))
    if size_occurrences != [0x18] or end_occurrences or field_pointer_occurrences:
        raise ValueError("whole-image size/end literal invariant mismatch")
    return {
        "source": source,
        "version": profile["version"],
        "sha256": digest,
        "header": {
            "declared_size": declared_size,
            "declared_size_occurrences": ["0x18"],
            "computed_end_address": f"0x{end_address:x}",
            "computed_end_literal_occurrences": 0,
            "size_field_pointer_occurrences": 0,
        },
        "startup": {
            "entry": f"0x{profile['entry']:x}",
            "runtime_initializer": f"0x{profile['runtime']:x}",
            "main": f"0x{profile['main']:x}",
            "initializer_records": [
                {"operation": "zero RAM", "target": f"0x{zero['target']:x}",
                 "bytes": zero["length"], "ram_start": f"0x{zero['source']:x}"},
                {"operation": "copy ROM to RAM", "target": f"0x{copy['target']:x}",
                 "bytes": copy["length"], "source_offset": f"0x{copy['source']:x}",
                 "ram_start": f"0x{copy['destination']:x}"},
            ],
        },
        "structured_tail_verified": True,
        "bounded_conclusion": (
            "the application startup path has no direct whole-image size/end literal "
            "and initializes RAM before main; no appended opaque signature trailer is "
            "identified in this exact image"
        ),
        "limitations": [
            "does not inspect the resident motor bootloader",
            "literal absence does not exclude computed addresses or an external integrity record",
            "does not prove that a modified image is accepted, boots, or remains recoverable over BLE",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("images", type=Path, nargs="+")
    arguments = parser.parse_args()
    try:
        results = [inspect(image.read_bytes(), image.name) for image in arguments.images]
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")
    print(json.dumps(results[0] if len(results) == 1 else results, indent=2))


if __name__ == "__main__":
    main()
