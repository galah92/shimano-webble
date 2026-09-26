#!/usr/bin/env python3
"""Verify the exact E5000 D4.5.0 B0/B4/BC policy without dumping firmware.

The vendor image stays outside Git. This read-only checker accepts only the
recorded raw D4.5.0 analysis image, verifies the cumulative-dispatch cases,
setter call graph, destination ceilings, persistence record, and response
builders, then emits a compact JSON conclusion.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path


LOAD_BASE = 0x10000
EXPECTED_SIZE = 138_072
EXPECTED_SHA256 = "44806bd54aedff95a88bb73fafe0f0581297f2f67b2ea35545cea012899d90bb"


def offset(address):
    return address - LOAD_BASE


def read_u32(data, address):
    return struct.unpack_from("<I", data, offset(address))[0]


def require_bytes(data, address, expected_hex, label):
    expected = bytes.fromhex(expected_hex)
    actual = data[offset(address):offset(address) + len(expected)]
    if actual != expected:
        raise ValueError(f"{label} signature mismatch at 0x{address:x}")


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


def require_call(data, address, target, label):
    actual = thumb_bl_target(data, address)
    if actual != target:
        raise ValueError(
            f"{label} call mismatch at 0x{address:x}: 0x{actual:x}"
        )


def inspect(data, source):
    digest = hashlib.sha256(data).hexdigest()
    if len(data) != EXPECTED_SIZE or digest != EXPECTED_SHA256:
        raise ValueError(f"{source}: not the exact recorded raw D4.5.0 image")

    # These are cumulative-subtraction compare sites, not literal opcode keys.
    require_bytes(data, 0x1D74E, "0b3801d101f073fb", "16 B0 dispatch")
    require_bytes(data, 0x1D766, "0b3801d101f089fb", "16 B4 dispatch")
    require_bytes(data, 0x1D778, "153801d101f086fb", "16 BC dispatch")
    require_call(data, 0x1D752, 0x1EE3C, "B0 handler")
    require_call(data, 0x1D76A, 0x1EE80, "B4 handler")
    require_call(data, 0x1D77C, 0x1EE8C, "BC handler")

    require_call(data, 0x1EE3C, 0x243E0, "B0 PC-mode gate")
    require_call(data, 0x1EE48, 0x2C25A, "B0 u16 parser")
    require_call(data, 0x1EE54, 0x19264, "B0 persistent setter")
    require_bytes(data, 0x1EE5C, "2e2000f0aeff", "B0 success event 0x2E")

    require_call(data, 0x19268, 0x178C8, "current-destination reader")
    require_call(data, 0x1926E, 0x193EE, "destination-ceiling reader")
    require_bytes(
        data, 0x19274, "3800210080b289b2884201d2002621e0ba4d",
        "reject-only-above-ceiling comparison",
    )
    require_bytes(
        data, 0x1929E,
        "6946282010f099f910f0d2f9282010f0e3f906003000c0b2012806d12c80",
        "record-0x28 persistence and live update",
    )
    require_call(data, 0x192A2, 0x295D8, "record-0x28 stage")
    require_call(data, 0x192A6, 0x2964E, "settings commit")
    require_call(data, 0x192AC, 0x29676, "record-0x28 verification")
    require_call(data, 0x192BC, 0x17316, "assist recalculation")
    require_call(data, 0x192C0, 0x1873C, "dependent-state refresh")

    require_bytes(
        data, 0x193EE,
        "00b501000800c0b2002805d0022807d004d3042800d006d29c4805e09c4803e0"
        "9620000100e0984880b200bd",
        "destination ceiling helper",
    )
    if read_u32(data, 0x19678) != 2500 or read_u32(data, 0x1967C) != 3218:
        raise ValueError("destination ceiling literals mismatch")

    expected_words = {
        0x23220: 0xB216,  # B0 success response
        0x23224: 0xB616,  # configured maximum reply
        0x2318C: 0xBE16,  # per-destination maximum reply
        0x245F0: 0x200029F9,  # global PC-mode byte
        0x232C0: 0x20002971,  # BC selector byte
        0x19570: 0x20000472,  # configured maximum
        0x10B9C: 0x22E9D,  # event 0x2E builder (Thumb pointer)
        0x10BA0: 0x22F1D,  # event 0x2F builder (Thumb pointer)
    }
    for address, expected in expected_words.items():
        if read_u32(data, address) != expected:
            raise ValueError(f"policy word mismatch at 0x{address:x}")

    require_call(data, 0x22EEE, 0x192D4, "B4 current-value reader")
    require_call(data, 0x22F40, 0x193EE, "BC destination-ceiling reader")

    return {
        "source": source,
        "version": "D4.5.0",
        "sha256": digest,
        "dispatch": {
            "16 B0": "0x1ee3c",
            "16 B4": "0x1ee80",
            "16 BC": "0x1ee8c",
        },
        "b0_policy": {
            "required_pc_mode": "nonzero",
            "persistent_record": "0x28",
            "normal_reply": "16 B2",
            "rejects": "requested value above current destination ceiling",
        },
        "destination_ceiling_hundredths_kmh": {
            "EU_0": 2500,
            "US_1": 3218,
            "Japan_2": 2400,
            "Taiwan_3": 2500,
            "Korea_4": 2500,
        },
        "safe_us_client_target_hundredths_kmh": 3200,
        "bounded_conclusion": (
            "the exact stock D4.5.0 policy permits B0=3200 after destination=1 "
            "while its internal US ceiling is 3218"
        ),
        "limitations": [
            "does not send a BLE command",
            "does not prove SC-E7000 transport timing or a live response",
            "does not prove persistence after a physical power cycle or riding cutoff",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path)
    arguments = parser.parse_args()
    try:
        result = inspect(arguments.image.read_bytes(), arguments.image.name)
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
