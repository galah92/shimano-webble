#!/usr/bin/env python3
"""Verify the exact SM-PCE02 3.0.4 generic unit-command transport.

The vendor image stays outside Git. This read-only tool identifies the exact
raw image recorded in ASSETS.md, checks the startup metadata, opcode table, and
small function slices behind the transport analysis, and emits JSON without
dumping firmware bytes.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path


LOAD_BASE = 0x10000
IMAGE_SIZE = 64_360
IMAGE_SHA256 = "93e7889d678ec943cd99b32ba193777df1dacff86558b666d37147f72298d777"

VECTOR_OFFSET = 0x5E4
STACK_POINTER = 0x20000868
RESET_HANDLER_THUMB = 0x0001ABA1

INIT_RECORD_OFFSET = 0xF7E4
INIT_RECORD = bytes.fromhex("e71dffff0c000000e00600000c000020")
INIT_HANDLER_THUMB = 0x000115CB
SPECIAL_TABLE_OFFSET = 0xF7F4
SPECIAL_PAIRS = (
    (0x30, 0x2A),
    (0x01, 0x18),
    (0x01, 0x1A),
    (0x01, 0x2C),
    (0x01, 0x2E),
    (0x01, 0x0C),
    (0x01, 0x0E),
    (0x01, 0x24),
    (0x01, 0x26),
    (0x01, 0x5C),
    (0x01, 0x5E),
    (0x02, 0x08),
    (0x01, 0x00),
    (0x01, 0x02),
)
SPECIAL_TABLE = bytes(value for pair in SPECIAL_PAIRS for value in pair)

FUNCTION_SLICES = {
    "control_dispatch": {
        "address": 0x11240,
        "size": 596,
        "sha256": "9495460b265189a6b67510fb9c45ec309f64b95d61d33fda68b0f55ad70ab857",
    },
    "generic_0x48_handler": {
        "address": 0x166E2,
        "size": 56,
        "sha256": "781591b9893e7af20d24354d629694ca7fe7a444e2d9d96b0e63a4091c07f948",
    },
    "special_pair_checker": {
        "address": 0x1BC42,
        "size": 72,
        "sha256": "6603c41ff4e563a2bbd700bb1db6d61dfcfe33da0fe5328e98c8f22c7c752ec1",
    },
    "bus_packetizer": {
        "address": 0x1E15C,
        "size": 320,
        "sha256": "e5d21ee99eb958ce609fa2ba53712d81c1ab2aae56a24610f61d183aa66a4fe4",
    },
}


def function_slice(data, address, size):
    offset = address - LOAD_BASE
    result = data[offset:offset + size]
    if len(result) != size:
        raise ValueError(f"function slice at 0x{address:x} is outside the image")
    return result


def inspect(data, source_name):
    digest = hashlib.sha256(data).hexdigest()
    if len(data) != IMAGE_SIZE or digest != IMAGE_SHA256:
        raise ValueError(
            f"{source_name}: image is not the exact recorded SM-PCE02 3.0.4 sample"
        )

    stack_pointer, reset_handler = struct.unpack_from("<II", data, VECTOR_OFFSET)
    if (stack_pointer, reset_handler) != (STACK_POINTER, RESET_HANDLER_THUMB):
        raise ValueError("vector-like stack/reset pair mismatch")

    init_record = data[INIT_RECORD_OFFSET:INIT_RECORD_OFFSET + len(INIT_RECORD)]
    if init_record != INIT_RECORD:
        raise ValueError("opcode-table initializer record mismatch")
    relative_handler, source_relative, byte_count, destination = struct.unpack(
        "<iIII", init_record
    )
    record_address = LOAD_BASE + INIT_RECORD_OFFSET
    if record_address + relative_handler != INIT_HANDLER_THUMB:
        raise ValueError("initializer handler pointer mismatch")
    if (source_relative, byte_count, destination) != (0x0C, 0x6E0, 0x2000000C):
        raise ValueError("initializer source/size/destination metadata mismatch")

    table = data[SPECIAL_TABLE_OFFSET:SPECIAL_TABLE_OFFSET + len(SPECIAL_TABLE)]
    if table != SPECIAL_TABLE:
        raise ValueError("opcode-aware special-pair table mismatch")
    if (0x16, 0xA0) in SPECIAL_PAIRS or (0x16, 0xA8) in SPECIAL_PAIRS:
        raise ValueError("destination transaction unexpectedly appears in special-pair table")

    verified_functions = {}
    for name, profile in FUNCTION_SLICES.items():
        actual = hashlib.sha256(
            function_slice(data, profile["address"], profile["size"])
        ).hexdigest()
        if actual != profile["sha256"]:
            raise ValueError(f"{name} function-slice fingerprint mismatch")
        verified_functions[name] = {
            "address": f"0x{profile['address']:x}",
            "bytes": profile["size"],
            "sha256": actual,
        }

    return {
        "source": source_name,
        "image": {
            "family": "SM-PCE02 adapter",
            "version": "3.0.4",
            "size": len(data),
            "sha256": digest,
            "load_base": f"0x{LOAD_BASE:x}",
            "stack_pointer": f"0x{stack_pointer:x}",
            "reset_handler_thumb": f"0x{reset_handler:x}",
        },
        "transport": {
            "serial_control_byte": "0x48",
            "generic_handler": "0x166e2",
            "verified_call_chain": [
                "0x166e2",
                "0x1873c",
                "0x19206",
                "0x1b8a4",
                "0x1beec",
                "0x1e15c",
            ],
            "special_pair_table_ram": "0x2000000c",
            "special_pairs": [
                {"group": f"0x{group:02x}", "opcode": f"0x{opcode:02x}"}
                for group, opcode in SPECIAL_PAIRS
            ],
            "group_16_opcode_a0_is_special": False,
            "group_16_opcode_a8_is_special": False,
            "function_slices": verified_functions,
        },
        "conclusion": (
            "in this exact image the 0x48 handler strips serial control and slot, "
            "copies the unit-command bytes unchanged, and group 0x16 opcodes 0xa0 "
            "and 0xa8 take the ordinary bus packetizer; no hidden A0 insertion or "
            "A8 rewrite exists in this verified path"
        ),
        "limitations": [
            "static result for the exact SM-PCE02 3.0.4 image only",
            "function semantics come from the bounded decompilation documented in the repository",
            "does not cover SM-PCE1 firmware or an unobserved command sent elsewhere in a host workflow",
            "does not replace a live PCE bus trace or prove a destination write on the bike",
        ],
    }


def run_self_test(data):
    inspect(data, "self-test exact image")
    modified = bytearray(data)
    modified[FUNCTION_SLICES["generic_0x48_handler"]["address"] - LOAD_BASE] ^= 0x01
    try:
        inspect(bytes(modified), "self-test modified image")
    except ValueError:
        return True
    raise ValueError("modified-image self-test was not rejected")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path)
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="also prove that a one-byte-modified in-memory sample is rejected",
    )
    args = parser.parse_args()
    try:
        with args.image.open("rb") as source:
            data = source.read()
        result = inspect(data, args.image.name)
        if args.self_test:
            result["modified_sample_rejected"] = run_self_test(data)
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
