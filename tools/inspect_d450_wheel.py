#!/usr/bin/env python3
"""Bounded static check of the stock D4.5.0 category-35 wheel handlers.

This does not establish that a phone command passes the live source-state gate.
The exact private vendor image is read in place and never copied or emitted.
"""
import argparse
import hashlib
import json
from pathlib import Path

from inspect_motor_max_assist import (
    EXPECTED_SHA256, EXPECTED_SIZE, read_u32, require_bytes, require_call,
)


def inspect(data):
    if len(data) != EXPECTED_SIZE or hashlib.sha256(data).hexdigest() != EXPECTED_SHA256:
        raise ValueError("not the exact recorded raw D4.5.0 image")

    # The dispatcher compares successive differences. These cumulative keys
    # are 0x0035 (35 00) and 0x0435 (35 04), not opcode literals in the image.
    if read_u32(data, 0x1D820) != 0x3C3:
        raise ValueError("category-35 dispatch interval changed")
    require_bytes(data, 0x1D4CA, "0f3801d1", "35 00 comparison")
    require_call(data, 0x1D4CE, 0x1E13C, "35 00 handler")
    require_bytes(data, 0x1D502, "c01e01d1", "35 04 comparison")
    require_call(data, 0x1D506, 0x1E1BC, "35 04 handler")

    require_call(data, 0x1E13C, 0x243E0, "35 00 PC-mode check")
    require_call(data, 0x1E148, 0x2C25A, "35 00 value parser")
    require_bytes(data, 0x1E150, "0e482100827fc9b2914220d1017e807f8142",
                  "35 00 source-state gate")
    require_call(data, 0x1E168, 0x2C25A, "35 00 accepted-value parser")
    require_call(data, 0x1E16E, 0x18E38, "35 00 persistent setter")
    require_call(data, 0x18E5A, 0x295D8, "wheel record 0x1f stage")
    require_call(data, 0x18E5E, 0x2964E, "wheel settings commit")
    require_call(data, 0x18E64, 0x29676, "wheel record 0x1f verification")
    require_call(data, 0x1E1C2, 0x20E78, "35 04 read response")
    if read_u32(data, 0x1E18C) != 0x20002168:
        raise ValueError("category-35 source-state pointer changed")

    return {
        "image": "exact raw D4.5.0",
        "dispatch": {"35 00": "0x1e13c", "35 04": "0x1e1bc"},
        "setter": {
            "required_pc_mode": "nonzero",
            "requires": "nonzero u16 value and source-state equality/inequality gate",
            "persistent_record": "0x1f",
            "live_ble_acceptance": "unverified",
        },
        "getter": "35 04 schedules a read response; live BLE reply unverified",
        "limitation": "A retained firmware handler is not proof that SC-E7000 forwards or the bike accepts a phone setting write.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path)
    args = parser.parse_args()
    try:
        result = inspect(args.image.read_bytes())
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
