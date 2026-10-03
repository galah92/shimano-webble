#!/usr/bin/env python3
"""Verify exact display serial-event routing; read-only, no bike connection."""
import argparse
import hashlib
import json
import struct
from pathlib import Path

from inspect_display_pc_mode import EXPECTED_SHA256, EXPECTED_SIZE, file_offset, require_bytes, thumb_bl_targets


def serial_event_route(data, event_type):
    """Evaluate only this bounded Thumb-16 CMP/SUB/branch dispatch, not firmware."""
    address = 0x28BD0
    register = event_type
    zero = carry = False
    for _ in range(100):
        if not 0x28BD0 <= address < 0x28C62:
            return address
        instruction = struct.unpack_from("<H", data, file_offset(address))[0]
        here = address
        address += 2
        if instruction & 0xF800 == 0x2800 and (instruction >> 8) & 7 == 1:
            immediate = instruction & 0xFF
            zero, carry = register == immediate, register >= immediate
        elif instruction & 0xF800 == 0x3800 and (instruction >> 8) & 7 == 1:
            immediate = instruction & 0xFF
            carry = register >= immediate
            register = (register - immediate) & 0xFFFFFFFF
            zero = register == 0
        elif instruction & 0xFE00 == 0x1E00 and instruction & 0x3F == 9:
            immediate = (instruction >> 6) & 7
            carry = register >= immediate
            register = (register - immediate) & 0xFFFFFFFF
            zero = register == 0
        elif instruction & 0xF000 == 0xD000:
            condition = (instruction >> 8) & 15
            predicates = {0: zero, 1: not zero, 3: not carry,
                          8: carry and not zero, 9: not carry or zero}
            if condition not in predicates:
                raise ValueError(f"Unexpected branch condition at 0x{here:x}")
            if predicates[condition]:
                displacement = instruction & 0xFF
                if displacement & 0x80:
                    displacement -= 0x100
                address = here + 4 + displacement * 2
        elif instruction & 0xF800 == 0xE000:
            displacement = instruction & 0x7FF
            if displacement & 0x400:
                displacement -= 0x800
            address = here + 4 + displacement * 2
        else:
            raise ValueError(f"Unexpected dispatch instruction at 0x{here:x}")
    raise ValueError("Dispatch failed to terminate")


def inspect(data):
    if len(data) != EXPECTED_SIZE or hashlib.sha256(data).hexdigest() != EXPECTED_SHA256:
        raise ValueError("Expected exact stock SC-E7000 4.1.0 plaintext image")
    for address, signature, label in [
        (0x28AE8, "314a5218921e1070491ce173", "serial payload copied into event buffer"),
        (0x28B02, "a17b814205d10120a072072002f029fa10bd", "XOR checksum acceptance"),
        (0x28E58, "43480178012919d000d288e0032906d009d3042900d082e0eff76afa7fe0", "subtype-4 lifecycle call"),
        (0x1834A, "fdf7e9fe012801d107f031fa", "setup-flag-gated rearm"),
    ]:
        require_bytes(data, address, bytes.fromhex(signature), label)
    routes = {value: serial_event_route(data, value) for value in range(256)}
    if [value for value, target in routes.items() if target == 0x28E58] != [0x91]:
        raise ValueError("Lifecycle event dispatch mismatch")
    if routes[0x20] != 0x28DCC or routes[0x10] != 0x28D1A:
        raise ValueError("Separate data-event paths mismatch")
    if struct.unpack_from("<I", data, file_offset(0x276E4))[0] != 0x28A8D:
        raise ValueError("Serial receive callback literal mismatch")
    if struct.unpack_from("<I", data, file_offset(0x15D7C + (0x84 >> 1) * 4))[0] != 0x204E1:
        raise ValueError("Display component-version dispatch mismatch")
    require_bytes(data, 0x197AE, bytes.fromhex(
        "6846fef7f5fc68468178002901d1392007e0c27812020a433a800079"),
        "radio selector reads cache, rejects missing cached version")
    if thumb_bl_targets(data, 0x1819E, 0x181A6) != [0x283CC]:
        raise ValueError("Radio cache getter mismatch")
    if thumb_bl_targets(data, 0x283CC, 0x28414):
        raise ValueError("Cache-copy getter unexpectedly has a direct call")
    return {
        "image_sha256": EXPECTED_SHA256,
        "serial_receive_callback": "0x28a8c",
        "serial_event_worker": "0x28bb8",
        "lifecycle_route": "event type 0x91 -> 0x28e58; payload subtype 4 -> 0x18348",
        "rearm_condition": "0x18348 calls 0x1f7b8 only when setup getter 0x16120 returns 1",
        "separate_data_routes": {"0x10": hex(routes[0x10]), "0x20": hex(routes[0x20])},
        "dispatch_inputs_checked": 256,
        "radio_component_version_read": {
            "display_packet": "00 13 01 84 01",
            "reply_prefix": "33 01 86",
            "error_prefix": "33 01 87",
            "path": "0x204e0 -> 0x19780(1) -> 0x1819e -> 0x283cc cache copy",
            "missing_cache_error": "39",
            "role": "cached component-version read; no radio command or firmware transfer",
        },
        "limitations": [
            "Does not identify the vendor meaning or radio-module producer of event 0x91 subtype 4",
            "Does not show this event occurred during a bike test",
            "Separate immediate routes do not exclude a later asynchronous lifecycle event",
            "Does not authorize another setting write, journal bypass, or firmware transfer",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path)
    args = parser.parse_args()
    try:
        with args.image.open("rb") as source:
            result = inspect(source.read(EXPECTED_SIZE + 1))
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
