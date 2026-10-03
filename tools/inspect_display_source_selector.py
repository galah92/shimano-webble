#!/usr/bin/env python3
"""Check exact SC-E7000 selector/transport evidence; never communicate with a bike."""
import argparse
import hashlib
import json
import struct
from pathlib import Path

from inspect_display_pc_mode import (
    EXPECTED_SHA256, EXPECTED_SIZE, file_offset, require_bytes, thumb_bl_targets,
)


def inspect(data):
    if len(data) != EXPECTED_SIZE or hashlib.sha256(data).hexdigest() != EXPECTED_SHA256:
        raise ValueError("Expected the exact stock SC-E7000 4.1.0 plaintext image")

    signatures = {
        0x2359C: ("40203840a07020203840e070f806c00e2071", "separate selector fields"),
        0x21276: ("80b5804908700af03efd01bd", "transport selector helper"),
        0x1F9C6: ("ae4988717047", "requested interface-state helper"),
        0x2BD32: ("c749887101f059fc01f02ffe02f099f81ce0", "transport reset calls"),
        0x235CE: ("0120fdf751fef1bd0020fdf74dfe", "flag selects helper argument 1 or 0"),
    }
    for address, (signature, label) in signatures.items():
        require_bytes(data, address, bytes.fromhex(signature), label)

    def literal(address, expected):
        value = struct.unpack_from("<I", data, file_offset(address))[0]
        if value != expected:
            raise ValueError(f"Literal mismatch at 0x{address:x}")

    for address, value in [(0x236F4, 0x200006B4), (0x2147C, 0x20000218),
                           (0x1FC80, 0x200006E7), (0x2C050, 0x2000000C)]:
        literal(address, value)

    calls = thumb_bl_targets(data, 0x23508, 0x235F0)
    if not {0x16110, 0x201E2, 0x1F9C6, 0x21276}.issubset(calls):
        raise ValueError("Selector setter call graph mismatch")
    reset_calls = thumb_bl_targets(data, 0x2BD32, 0x2BD44)
    if reset_calls != [0x2D5EC, 0x2D99C, 0x2DE74]:
        raise ValueError("Transport-reset call graph mismatch")
    lifecycle_calls = thumb_bl_targets(data, 0x1FAAA, 0x1FB96)
    if not {0x2BF22, 0x22282, 0x21A76}.issubset(lifecycle_calls):
        raise ValueError("Interface lifecycle call graph mismatch")

    return {
        "image_sha256": EXPECTED_SHA256,
        "selector_setter": "0x23508",
        "selector_getter": "0x235f0",
        "state": "0x200006b4: +2=bit40, +3=bit20, +4=explicit selector, +5=automatic selector",
        "getter_forms": {
            "bit40_set": "0xc0 | bit20 | explicit selector",
            "bit40_clear": "0x80 | bit20 | automatic selector (unless bit20 or automatic=0xff)",
        },
        "bit40_helper": "0x21276 stores flag at 0x20000218, then calls 0x2bcfc",
        "transport_flag": "0x2bcfc stores helper argument at bus state 0x2000000c+6",
        "transport_reset_calls": [hex(x) for x in reset_calls],
        "interface_request": "0x1f9c6 stores 2 (bit20 clear) or 3 (bit20 set) at 0x200006e7+6",
        "interface_transition": "0x1faaa compares requested/current; a change resets transport and connection state",
        "physical_observation": "24 CD then 24 8D; neither is a protected motor-mode readback",
        "limitations": [
            "Static exact-image evidence only, not runtime queue or motor-mode observation",
            "Does not establish retaining bit40 fixes A0 rejection",
            "Does not authorize a selector change, A0 retry, journal clear, or firmware transfer",
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
