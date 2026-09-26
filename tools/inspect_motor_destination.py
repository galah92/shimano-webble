#!/usr/bin/env python3
"""Verify the E5000 D4.1/D4.3/D4.5 A0-to-A8 destination gate.

Vendor images stay outside Git. This read-only tool identifies one or more
exact raw images recorded in ASSETS.md, checks the small control-flow and RAM
invariants behind the destination analysis, and emits JSON without dumping
firmware bytes.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path


LOAD_BASE = 0x10000

PROFILES = {
    "fdb0f40b94d55ce9d098f803fe0f2f4038a3ce3343fe539bf151a9511dda14ec": {
        "version": "D4.1.0",
        "size": 135_052,
        "header_version_byte": 0x41,
        "entry": 0x2EBB8,
        "runtime_init": 0x30B20,
        "initializer_table": 0x30BC8,
        "zero_routine": 0x30B8C,
        "a0": 0x240E0,
        "a8": 0x241B0,
        "record_helper": 0x24356,
        "pc_request": 0x26098,
        "pc_secure": 0x262AC,
        "pc_slot": 0x20002D6D,
        "active_mode": 0x20002D6E,
        "requested_mode": 0x20002D6F,
        "secure_word_count": 0x20002D70,
        "gate": 0x20002D72,
        "candidate_head": 0x200028D0,
        "candidate_tail": 0x200028D5,
        "literal_addresses": {
            "active_mode": [0x243D0],
            "gate": [0x243D8],
            "candidate_head": [0x243D4],
            "candidate_tail": [0x243E0],
        },
        "dispatch_a0": [0x118F8, 0x11CE8],
        "dispatch_a8": [0x11908, 0x11CF8],
        "dispatch_pc_request": [0x11978],
        "dispatch_pc_secure": [0x119B8],
        "pc_request_prologue": "f1b5",
        "pc_secure_prologue": "70b5",
        "pc_stage_signature": (
            0x260FE,
            "f6b2042e02d0f6b2052e07d16448067064480570002063490870b0e0",
        ),
        "pc_promote_signature": (
            0x2633C,
            "96480078052830db92480078234908700020924908700120fef7ddfa0020ac49",
        ),
        "mode_tables": {1: 0x11794, 4: 0x117A0, 5: 0x117AC},
        "a0_mode_signature": (0x240F0, "b7480078042803d0b548007805282ed1"),
        "a0_zero_signature": (0x24100, "0221a81cc9b2405c0700ffb2002f26d1"),
        "a0_gate_set_signature": (0x2411A, "0120ae490870"),
        "a8_mode_gate_signature": (
            0x241C0,
            "83480078042803d081480078052827d181480078012823d1",
        ),
        "a8_gate_clear": 0x241E2,
        "a8_gate_clear_signature": "00207c490870",
        "a8_helper_call": 0x241E8,
    },
    "3d3df4dfe3de333062f445b6719fa5033f93dc9d384448134ee6041d216c6af0": {
        "version": "D4.3.0",
        "size": 132_072,
        "header_version_byte": 0x43,
        "entry": 0x2E214,
        "runtime_init": 0x2FF20,
        "initializer_table": 0x2FFCC,
        "zero_routine": 0x2FF90,
        "a0": 0x23B74,
        "a8": 0x23C48,
        "record_helper": 0x23DE2,
        "pc_request": 0x25AE8,
        "pc_secure": 0x25CFC,
        "pc_slot": 0x2000295A,
        "active_mode": 0x2000295B,
        "requested_mode": 0x2000295C,
        "secure_word_count": 0x2000295D,
        "gate": 0x2000295F,
        "candidate_head": 0x200024D0,
        "candidate_tail": 0x200024D5,
        "literal_addresses": {
            "active_mode": [0x23C30, 0x23E6C],
            "gate": [0x23E64],
            "candidate_head": [0x23E60],
            "candidate_tail": [0x23E70],
        },
        "dispatch_a0": [0x119A0, 0x11D90],
        "dispatch_a8": [0x119B0, 0x11DA0],
        "dispatch_pc_request": [0x11A20],
        "dispatch_pc_secure": [0x11A60],
        "pc_request_prologue": "f3b5",
        "pc_secure_prologue": "f1b5",
        "pc_stage_signature": (
            0x25B52,
            "3000c0b2042803d03000c0b2052807d16348067063480570002062490870b2e0",
        ),
        "pc_promote_signature": (
            0x25D7A,
            "9848017805292adb234e217831700025290001700120fef7c0fa2800b1490870",
        ),
        "mode_tables": {1: 0x1183C, 4: 0x11848, 5: 0x11854},
        "a0_mode_signature": (0x23B88, "29480178042902d0007805282dd1"),
        "a0_zero_signature": (0x23B96, "0221b01cc9b2405c694608766846007e002823d1"),
        "a0_gate_set_signature": (0x23BB6, "ab480470"),
        "a8_mode_gate_signature": (
            0x23C54,
            "85480178042902d00078052824d1804c2078012820d1",
        ),
        "a8_gate_clear": 0x23C78,
        "a8_gate_clear_signature": "00252570",
        "a8_helper_call": 0x23C7C,
    },
    "44806bd54aedff95a88bb73fafe0f0581297f2f67b2ea35545cea012899d90bb": {
        "version": "D4.5.0",
        "size": 138_072,
        "header_version_byte": 0x45,
        "entry": 0x2F984,
        "runtime_init": 0x31690,
        "initializer_table": 0x3173C,
        "zero_routine": 0x31700,
        "a0": 0x252A8,
        "a8": 0x2537C,
        "record_helper": 0x25516,
        "pc_request": 0x2721C,
        "pc_secure": 0x27430,
        "pc_slot": 0x200029F8,
        "active_mode": 0x200029F9,
        "requested_mode": 0x200029FA,
        "secure_word_count": 0x200029FB,
        "gate": 0x200029FD,
        "candidate_head": 0x20002548,
        "candidate_tail": 0x2000254D,
        "literal_addresses": {
            "active_mode": [0x25364, 0x255A0],
            "gate": [0x25598],
            "candidate_head": [0x25594],
            "candidate_tail": [0x255A4],
        },
        "dispatch_a0": [0x11B50, 0x11F40],
        "dispatch_a8": [0x11B60, 0x11F50],
        "dispatch_pc_request": [0x11BD0],
        "dispatch_pc_secure": [0x11C10],
        "pc_request_prologue": "f3b5",
        "pc_secure_prologue": "f1b5",
        "pc_stage_signature": (
            0x27286,
            "3000c0b2042803d03000c0b2052807d16348067063480570002062490870b2e0",
        ),
        "pc_promote_signature": (
            0x274AE,
            "9848017805292adb234e217831700025290001700120fef7c0fa2800b1490870",
        ),
        "mode_tables": {1: 0x119EC, 4: 0x119F8, 5: 0x11A04},
        "a0_mode_signature": (0x252BC, "29480178042902d0007805282dd1"),
        "a0_zero_signature": (0x252CA, "0221b01cc9b2405c694608766846007e002823d1"),
        "a0_gate_set_signature": (0x252EA, "ab480470"),
        "a8_mode_gate_signature": (
            0x25388,
            "85480178042902d00078052824d1804c2078012820d1",
        ),
        "a8_gate_clear": 0x253AC,
        "a8_gate_clear_signature": "00252570",
        "a8_helper_call": 0x253B0,
    },
}

MODE_TABLE_BYTES = {
    1: "a22b300e7a4d622b85b4",
    4: "19b273d8a473b1720110",
    5: "270f115535b003f30903",
}


def file_offset(address):
    return address - LOAD_BASE


def read_u32(data, address):
    return struct.unpack_from("<I", data, file_offset(address))[0]


def require_bytes(data, address, expected_hex, label):
    expected = bytes.fromhex(expected_hex)
    actual = data[file_offset(address):file_offset(address) + len(expected)]
    if actual != expected:
        raise ValueError(f"{label} signature mismatch at 0x{address:x}")


def thumb_bl_target(data, address):
    """Decode one Thumb-2 BL instruction at an already identified address."""
    first, second = struct.unpack_from("<HH", data, file_offset(address))
    if first & 0xF800 != 0xF000 or second & 0xD000 != 0xD000:
        raise ValueError(f"expected Thumb BL at 0x{address:x}")
    sign = (first >> 10) & 1
    imm10 = first & 0x03FF
    j1 = (second >> 13) & 1
    j2 = (second >> 11) & 1
    imm11 = second & 0x07FF
    i1 = 1 ^ (j1 ^ sign)
    i2 = 1 ^ (j2 ^ sign)
    immediate = ((sign << 24) | (i1 << 23) | (i2 << 22)
                 | (imm10 << 12) | (imm11 << 1))
    if sign:
        immediate -= 1 << 25
    return address + 4 + immediate


def u32_locations(data, value):
    needle = struct.pack("<I", value)
    locations = []
    start = 0
    while True:
        found = data.find(needle, start)
        if found < 0:
            return locations
        locations.append(LOAD_BASE + found)
        start = found + 1


def verify_locations(data, value, expected, label):
    actual = u32_locations(data, value)
    if actual != expected:
        rendered = ", ".join(f"0x{address:x}" for address in actual)
        raise ValueError(f"{label} locations mismatch: {rendered or 'none'}")
    return actual


def inspect(data, source_name):
    digest = hashlib.sha256(data).hexdigest()
    profile = PROFILES.get(digest)
    if profile is None:
        raise ValueError(f"{source_name}: image fingerprint is not an exact recorded D4.1/D4.3/D4.5 sample")
    if len(data) != profile["size"]:
        raise ValueError(f"{source_name}: image size does not match its fingerprint profile")

    if data[0x10] != profile["header_version_byte"]:
        raise ValueError("raw header version marker mismatch")
    if read_u32(data, LOAD_BASE + 0x14) != profile["entry"] | 1:
        raise ValueError("raw header entry pointer mismatch")
    if read_u32(data, LOAD_BASE + 0x18) != len(data):
        raise ValueError("raw header image-size field mismatch")

    require_bytes(data, profile["a0"], "f0b5" if profile["version"] == "D4.1.0" else "f8b5",
                  "A0 handler prologue")
    require_bytes(data, profile["a8"], "70b5" if profile["version"] == "D4.1.0" else "f3b5",
                  "A8 handler prologue")
    for key in ("a0_mode_signature", "a0_zero_signature", "a0_gate_set_signature",
                "a8_mode_gate_signature"):
        address, signature = profile[key]
        require_bytes(data, address, signature, key)
    require_bytes(data, profile["a8_gate_clear"], profile["a8_gate_clear_signature"],
                  "A8 gate clear")
    if thumb_bl_target(data, profile["a8_helper_call"]) != profile["record_helper"]:
        raise ValueError("A8 persistent-record helper target mismatch")

    require_bytes(data, profile["pc_request"], profile["pc_request_prologue"],
                  "PC-mode request handler prologue")
    require_bytes(data, profile["pc_secure"], profile["pc_secure_prologue"],
                  "PC-mode secure-word handler prologue")
    for key in ("pc_stage_signature", "pc_promote_signature"):
        address, signature = profile[key]
        require_bytes(data, address, signature, key)
    for mode, address in profile["mode_tables"].items():
        require_bytes(data, address, MODE_TABLE_BYTES[mode], f"PC-mode {mode} secure table")

    literal_locations = {}
    for name in ("gate", "candidate_head", "candidate_tail"):
        literal_locations[name] = verify_locations(
            data, profile[name], profile["literal_addresses"][name], name
        )
    if profile["pc_slot"] != profile["active_mode"] - 1:
        raise ValueError("PC-mode application-slot adjacency invariant mismatch")
    if profile["requested_mode"] != profile["active_mode"] + 1:
        raise ValueError("PC-mode request-state adjacency invariant mismatch")
    if profile["secure_word_count"] != profile["active_mode"] + 2:
        raise ValueError("PC-mode secure-word counter adjacency invariant mismatch")
    if profile["gate"] != profile["secure_word_count"] + 2:
        raise ValueError("PC-mode/destination-gate separation invariant mismatch")
    if profile["candidate_tail"] != profile["candidate_head"] + 5:
        raise ValueError("A0/A8 pending-record adjacency invariant mismatch")

    verify_locations(data, profile["a0"] | 1, profile["dispatch_a0"], "A0 dispatch pointer")
    verify_locations(data, profile["a8"] | 1, profile["dispatch_a8"], "A8 dispatch pointer")
    verify_locations(
        data, profile["pc_request"] | 1, profile["dispatch_pc_request"],
        "PC-mode request dispatch pointer",
    )
    verify_locations(
        data, profile["pc_secure"] | 1, profile["dispatch_pc_secure"],
        "PC-mode secure-word dispatch pointer",
    )

    entry_call = profile["entry"] + 0x0E
    if thumb_bl_target(data, entry_call) != profile["runtime_init"]:
        raise ValueError("entry-to-runtime-initializer call mismatch")

    table = profile["initializer_table"]
    relative_call, zero_length, zero_start, terminator = struct.unpack_from(
        "<iIII", data, file_offset(table)
    )
    zero_target_thumb = table + relative_call
    if zero_target_thumb & ~1 != profile["zero_routine"]:
        raise ValueError("startup zero-routine target mismatch")
    if terminator != 0:
        raise ValueError("startup zero-record terminator mismatch")
    zero_end = zero_start + zero_length
    if not zero_start <= profile["gate"] < zero_end:
        raise ValueError("startup zero range does not cover the destination gate")

    return {
        "source": source_name,
        "image": {
            "family": "DU-E5000 D component",
            "version": profile["version"],
            "size": len(data),
            "sha256": digest,
            "entry": f"0x{profile['entry']:x}",
        },
        "destination_transaction": {
            "a0_handler": f"0x{profile['a0']:x}",
            "a8_handler": f"0x{profile['a8']:x}",
            "accepted_pc_modes": [4, 5],
            "a0_requires_zero_target": True,
            "a0_candidate": {
                "address": f"0x{profile['candidate_head']:x}",
                "bytes": 5,
            },
            "a0_sets_one_shot_gate": f"0x{profile['gate']:x}",
            "a8_requires_one_shot_gate": True,
            "a8_candidate": {
                "address": f"0x{profile['candidate_tail']:x}",
                "bytes": 6,
            },
            "a8_clears_gate_before_record_helper": True,
            "record_helper": f"0x{profile['record_helper']:x}",
            "pending_record_is_adjacent_11_bytes": True,
            "dispatch_pointer_locations": {
                "a0": [f"0x{address:x}" for address in profile["dispatch_a0"]],
                "a8": [f"0x{address:x}" for address in profile["dispatch_a8"]],
            },
        },
        "volatile_state": {
            "active_pc_mode": f"0x{profile['active_mode']:x}",
            "one_shot_gate": f"0x{profile['gate']:x}",
            "gate_offset_from_active_mode": 4,
            "exact_gate_literal_locations": [
                f"0x{address:x}" for address in literal_locations["gate"]
            ],
            "startup_zero_routine": f"0x{profile['zero_routine']:x}",
            "startup_zero_range": {
                "start": f"0x{zero_start:x}",
                "end_exclusive": f"0x{zero_end:x}",
                "bytes": zero_length,
            },
            "cold_boot_gate_prearmed": False,
        },
        "pc_mode_handshake": {
            "request_handler": f"0x{profile['pc_request']:x}",
            "secure_word_handler": f"0x{profile['pc_secure']:x}",
            "application_slot": f"0x{profile['pc_slot']:x}",
            "active_mode": f"0x{profile['active_mode']:x}",
            "requested_mode": f"0x{profile['requested_mode']:x}",
            "secure_word_count": f"0x{profile['secure_word_count']:x}",
            "destination_gate": f"0x{profile['gate']:x}",
            "destination_gate_offset_from_secure_word_count": 2,
            "secure_tables": {
                str(mode): {
                    "address": f"0x{address:x}",
                    "bytes": len(bytes.fromhex(MODE_TABLE_BYTES[mode])),
                    "sha256": hashlib.sha256(bytes.fromhex(MODE_TABLE_BYTES[mode])).hexdigest(),
                }
                for mode, address in profile["mode_tables"].items()
            },
            "modes_4_and_5_stage_without_setting_destination_gate": True,
            "fifth_matching_word_promotes_requested_mode_without_setting_destination_gate": True,
            "verified_direct_state_writes_exclude_destination_gate": True,
            "dispatch_pointer_locations": {
                "request": [
                    f"0x{address:x}" for address in profile["dispatch_pc_request"]
                ],
                "secure_word": [
                    f"0x{address:x}" for address in profile["dispatch_pc_secure"]
                ],
            },
        },
        "conclusion": (
            "this exact version keeps protected PC-mode establishment separate from "
            "the destination gate; mode 4 or 5 does not itself arm A8, A0 must create "
            "the volatile one-shot gate, and a cold start clears that gate"
        ),
        "limitations": [
            "static result for this exact raw image only",
            "exact-literal uniqueness does not prove absence of arbitrary computed-pointer writes",
            "does not establish what earlier official clients did before their direct A8 call",
            "does not prove BLE timing, persistence, or a higher physical assistance cutoff",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("images", type=Path, nargs="+")
    args = parser.parse_args()
    results = []
    try:
        for image in args.images:
            with image.open("rb") as source:
                data = source.read()
            results.append(inspect(data, image.name))
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")
    print(json.dumps(results[0] if len(results) == 1 else results, indent=2))


if __name__ == "__main__":
    main()
