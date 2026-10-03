#!/usr/bin/env python3
"""Inspect the exact public STEPS2 radio candidate in memory; never install it."""
import argparse
import hashlib
import json
import struct
from pathlib import Path

SIZE = 125032
SHA256 = "0a52a9240febce92e2a033122c02aeaa23eadbaf1c8648628974dc257e3b9fa1"


def decode_hex(data):
    memory = {}
    upper = 0
    ended = False
    for line in data.decode("ascii").splitlines():
        if ended or not line.startswith(":"):
            raise ValueError("Malformed Intel HEX framing")
        record = bytes.fromhex(line[1:])
        if len(record) < 5 or len(record) != record[0] + 5 or sum(record) % 256:
            raise ValueError("Intel HEX record length/checksum mismatch")
        address = int.from_bytes(record[1:3], "big")
        kind, payload = record[3], record[4:-1]
        if kind == 0:
            for offset, value in enumerate(payload):
                target = upper + address + offset
                if not 0x1D000 <= target < 0x28000 or target in memory:
                    raise ValueError("Overlapping or out-of-range candidate data")
                memory[target] = value
        elif kind == 4 and len(payload) == 2 and address == 0:
            upper = int.from_bytes(payload, "big") << 16
        elif kind == 5 and len(payload) == 4 and address == 0:
            pass  # Start-address record; vectors are independently checked below.
        elif kind == 1 and not payload and address == 0:
            ended = True
        else:
            raise ValueError("Unsupported Intel HEX record")
    if not ended or not memory:
        raise ValueError("Incomplete Intel HEX candidate")
    return memory


def inspect(data):
    if len(data) != SIZE or hashlib.sha256(data).hexdigest() != SHA256:
        raise ValueError("Expected exact STEPS2-ap 4.7.1 candidate; wrapped NRF2 is unsupported")
    memory = decode_hex(data)
    start, end = min(memory), max(memory) + 1
    vectors = bytes(memory[start + offset] for offset in range(8))
    stack, entry = struct.unpack("<II", vectors)
    if (start, end, stack, entry) != (0x1D000, 0x27D8A, 0x20002FE8, 0x27BD5):
        raise ValueError("Candidate range/vector mismatch")
    return {
        "sha256": SHA256, "size": SIZE,
        "address_range": [hex(start), hex(end)],
        "stack_pointer": hex(stack), "thumb_entry": hex(entry),
        "data_record_bytes": len(memory),
        "validation": "catalog candidate and HEX integrity only; exact-bike radio binding unverified",
        "installation": "not supported; no image output or bike communication",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path)
    args = parser.parse_args()
    try:
        with args.image.open("rb") as source:
            result = inspect(source.read(SIZE + 1))
    except (OSError, ValueError, UnicodeError) as error:
        parser.exit(1, f"{error}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
