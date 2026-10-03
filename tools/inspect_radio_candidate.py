#!/usr/bin/env python3
"""Inspect the exact public STEPS2 radio candidate in memory; never install it."""
import argparse
import hashlib
import json
import struct
from pathlib import Path

SIZE = 125032
SHA256 = "0a52a9240febce92e2a033122c02aeaa23eadbaf1c8648628974dc257e3b9fa1"


def serial_receive_route(memory, message_type):
    """Evaluate only the identified Thumb-16 CMP/branch type dispatcher."""
    if not 0 <= message_type <= 255:
        raise ValueError("Message type must be a byte")
    address = 0x1E68E
    zero = False
    for _ in range(100):
        if not 0x1E68E <= address < 0x1E74E:
            return address
        try:
            instruction = memory[address] | memory[address + 1] << 8
        except KeyError as error:
            raise ValueError("Missing dispatch instruction") from error
        here = address
        address += 2
        if instruction & 0xFF00 == 0x2B00:  # CMP r3, imm8
            zero = message_type == instruction & 255
        elif instruction & 0xFE00 == 0xD000:  # BEQ / BNE only
            condition = (instruction >> 8) & 1
            if zero != bool(condition):
                displacement = instruction & 255
                if displacement & 128:
                    displacement -= 256
                address = here + 4 + displacement * 2
        elif instruction & 0xF800 == 0xE000:
            displacement = instruction & 0x7FF
            if displacement & 0x400:
                displacement -= 0x800
            address = here + 4 + displacement * 2
        else:
            raise ValueError(f"Unexpected dispatch instruction at 0x{here:x}")
    raise ValueError("Dispatch failed to terminate")


def require_bytes(memory, address, signature):
    expected = bytes.fromhex(signature)
    if any(memory.get(address + offset) != value for offset, value in enumerate(expected)):
        raise ValueError(f"Radio signature mismatch at 0x{address:x}")


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
    # Sender stores the caller's type unchanged; it XORs type/length/payload.
    require_bytes(memory, 0x1D66E, "1a7059704a40")
    # This located 0x91 reply is F0/length 1, not subtype 04.
    require_bytes(memory, 0x1EC64, "f02069460870912201216846")
    # Standard command-status replies instead use type 20, length 4, subtype 40.
    require_bytes(memory, 0x1D47E, "4024147051709370")
    require_bytes(memory, 0x1D49C, "202204216846")
    # Distinct link-status sender: type 00, one cached status byte.
    require_bytes(memory, 0x1D40A, "80b501000748c172002201210b3000f011f9")
    require_bytes(memory, 0x1E0AC, "3888102809d0112832d0192868d0502800d1")
    require_bytes(memory, 0x1E17A, "2120fff745f9")
    require_bytes(memory, 0x1E1AE, "2020fff72bf9")
    require_bytes(memory, 0x1EDE0, "2020fef712fb")
    routes = {value: serial_receive_route(memory, value) for value in range(256)}
    if any(routes[value] != target for value, target in {
            0x10: 0x1E8CA, 0x11: 0x1E8DE, 0x80: 0x1EC24,
            0x90: 0x1EC54, 0x91: 0x1ECA2}.items()):
        raise ValueError("Radio receive-dispatch mismatch")
    return {
        "sha256": SHA256, "size": SIZE,
        "address_range": [hex(start), hex(end)],
        "stack_pointer": hex(stack), "thumb_entry": hex(entry),
        "data_record_bytes": len(memory),
        "serial_receive_routes": {hex(value): hex(routes[value])
                                  for value in (0x10, 0x11, 0x80, 0x90, 0x91)},
        "dispatch_inputs_checked": 256,
        "serial_reply_facts": {
            "sender": "0x1d63e copies the supplied type unchanged and adds XOR checksum",
            "located_91_reply": "0x1ec64 constructs type 91, length 1, payload F0",
            "ordinary_command_status": "0x1d474 constructs type 20, length 4, subtype 40",
            "link_status": "0x1d40a caches and sends type 00, length 1, caller's status byte",
            "status_21_origin": "stack event 11 in 0x1e09e can send 21 at 0x1e17a",
            "status_20_origins": "stack event 19 can send 20 at 0x1e1ae; 0x1edc0 can send 20 at 0x1ede0",
        },
        "validation": "catalog candidate and HEX integrity only; exact-bike radio binding unverified",
        "installation": "not supported; no image output or bike communication",
        "limitations": [
            "Receive routes and located constructors do not inventory all indirect transmitters",
            "Does not identify a producer of display event 91/04 or prove its absence",
            "Does not establish this candidate is the bike's radio image",
        ],
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
