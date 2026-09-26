#!/usr/bin/env python3
"""Compare display-owned PC mode in exact SC-E6100/SC-E7000 images.

The vendor images stay outside Git. This read-only verifier reports the small
historical bridge comparison relevant to the E5000 destination investigation.
It accepts SC-E6100 4.0.5 and SC-E7000 4.0.6/4.1.0; it does not dump firmware
bytes or make any image a repository dependency.
"""
import argparse
import hashlib
import json
from pathlib import Path

from inspect_display_pc_mode import (
    file_offset,
    thumb_bl_references,
    thumb_bl_targets,
)


PROFILES = {
    "9a3d9575af48eac883a2369af08bd00d819547c49c78d313d7aadc18269eeb77": {
        "model": "SC-E6100",
        "version": "4.0.5",
        "size": 164_488,
        "local": (0x2B88C, 0x2B8D6),
        "completion": (0x29EE0, 0x29F92),
        "completion_state": 0x29F2A,
        "post": (0x27950, 0x27962),
        "periodic": (0x2789C, 0x278B6),
        "rearm": (0x27962, 0x279C0),
        "exit": (0x279E0, 0x27A7A),
        "mode_tables": {"1": 0x29FB0, "4": 0x29FBC, "5": 0x29FC8},
        "local_calls": [0x29460, 0x1FC52, 0x1FC20, 0x29460, 0x27950],
        "completion_calls": [
            0x29340, 0x3417A, 0x35840, 0x2BF28, 0x3411A,
            0x341AA, 0x341AA, 0x2927A, 0x212A8,
        ],
        "post_calls": [0x21336],
        "periodic_calls": [0x279E0],
        "rearm_calls": [
            0x2B632, 0x279C6, 0x21344, 0x2B63E, 0x2B672,
            0x2B698, 0x279E0, 0x2B672, 0x2B698, 0x2B88C,
        ],
        "exit_calls": [0x2B63E, 0x2B88C, 0x27A78, 0x279C6, 0x27A78, 0x27918, 0x28396],
        "rearm_refs": [0x1F7BE, 0x1F83C, 0x1FAC4, 0x2027E],
        "exit_refs": [0x278B0, 0x2799A],
        "local_refs": [0x1DA58, 0x279BA, 0x27A04],
        "post_signature": "80b563480021817101714171f9f7ebfc01bd",
        "clears_phase_byte_3": False,
    },
    "ff934060d5a00e60817a153a557bde384ab2020ccbcd06c30a463549e62a3603": {
        "model": "SC-E7000",
        "version": "4.0.6",
        "size": 123_100,
        "local": (0x22D74, 0x22DBE),
        "completion": (0x213A4, 0x21456),
        "completion_state": 0x213EE,
        "post": (0x1EE1C, 0x1EE2E),
        "periodic": (0x1ED68, 0x1ED82),
        "rearm": (0x1EE2E, 0x1EE8C),
        "exit": (0x1EEAC, 0x1EF44),
        "mode_tables": {"1": 0x21474, "4": 0x21480, "5": 0x2148C},
        "local_calls": [0x20924, 0x17628, 0x175F6, 0x20924, 0x1EE1C],
        "completion_calls": [
            0x20804, 0x29F4A, 0x2B6C8, 0x2348C, 0x29EEA,
            0x29F7A, 0x29F7A, 0x2073E, 0x18C88,
        ],
        "post_calls": [0x18CDA],
        "periodic_calls": [0x1EEAC],
        "rearm_calls": [
            0x22B1A, 0x1EE92, 0x18CE8, 0x22B26, 0x22B5A,
            0x22B80, 0x1EEAC, 0x22B5A, 0x22B80, 0x22D74,
        ],
        "exit_calls": [0x22B26, 0x22D74, 0x1EF44, 0x1EE92, 0x1EF44, 0x1EDE4, 0x1F85A],
        "rearm_refs": [0x171A0, 0x17220, 0x1749C, 0x17C56],
        "exit_refs": [0x1ED7C, 0x1EE66],
        "local_refs": [0x15CCC, 0x1EE86, 0x1EED0],
        "post_signature": "80b563480021817101714171f9f757ff01bd",
        "clears_phase_byte_3": False,
    },
    "1f3c42ad0cc3e46d2e9affd5f023245f645acbc1c8ee3d68569bfcb25c9c3e79": {
        "model": "SC-E7000",
        "version": "4.1.0",
        "size": 126_508,
        "local": (0x236FC, 0x23746),
        "completion": (0x21D2C, 0x21DDE),
        "completion_state": 0x21D76,
        "post": (0x1F7A4, 0x1F7B8),
        "periodic": (0x1F6F0, 0x1F70A),
        "rearm": (0x1F7B8, 0x1F816),
        "exit": (0x1F836, 0x1F8CE),
        "mode_tables": {"1": 0x21DFC, "4": 0x21E08, "5": 0x21E14},
        "local_calls": [0x212AC, 0x17CFA, 0x17CC8, 0x212AC, 0x1F7A4],
        "completion_calls": [
            0x2118C, 0x2AC9A, 0x2C418, 0x23E14, 0x2AC3A,
            0x2ACCA, 0x2ACCA, 0x210C6, 0x19476,
        ],
        "post_calls": [0x194D0],
        "periodic_calls": [0x1F836],
        "rearm_calls": [
            0x234A2, 0x1F81C, 0x194DE, 0x234AE, 0x234E2,
            0x23508, 0x1F836, 0x234E2, 0x23508, 0x236FC,
        ],
        "exit_calls": [0x234AE, 0x236FC, 0x1F8CE, 0x1F81C, 0x1F8CE, 0x1F76C, 0x201E2],
        "rearm_refs": [0x17820, 0x178A6, 0x17B6C, 0x18352],
        "exit_refs": [0x1F704, 0x1F7F0],
        "local_refs": [0x16210, 0x1F810, 0x1F85A],
        "post_signature": "80b563480021817101714171c170f9f78dfe01bd",
        "clears_phase_byte_3": True,
    },
}


def require_bytes(data, address, expected_hex, label):
    expected = bytes.fromhex(expected_hex)
    actual = data[file_offset(address):file_offset(address) + len(expected)]
    if actual != expected:
        raise ValueError(f"{label} signature mismatch at 0x{address:x}")


def require_calls(data, bounds, expected, label):
    actual = thumb_bl_targets(data, *bounds)
    if actual != expected:
        raise ValueError(f"{label} call graph mismatch")
    return actual


def require_refs(data, target, expected, label):
    actual = thumb_bl_references(data, target)
    if actual != expected:
        raise ValueError(f"{label} whole-image references mismatch")
    return actual


def inspect(data, source_name):
    digest = hashlib.sha256(data).hexdigest()
    profile = PROFILES.get(digest)
    if profile is None or len(data) != profile["size"]:
        raise ValueError(
            f"{source_name}: expected exact SC-E6100 4.0.5 or SC-E7000 4.0.6/4.1.0 image"
        )

    local_start = profile["local"][0]
    require_bytes(data, local_start, "1cb5040005d0401e0dd0c01e01280ad9",
                  "local mode 0/1/4/5 selector")
    require_bytes(data, profile["completion_state"],
                  "1a4da9730020a0700120a8772078a874",
                  "successful secure completion state update")
    require_bytes(data, profile["post"][0], profile["post_signature"],
                  "post-request maintenance disarm")

    local_calls = require_calls(data, profile["local"], profile["local_calls"], "local mode")
    completion_calls = require_calls(
        data, profile["completion"], profile["completion_calls"], "secure completion"
    )
    post_calls = require_calls(data, profile["post"], profile["post_calls"], "post-request")
    periodic_calls = require_calls(
        data, profile["periodic"], profile["periodic_calls"], "periodic maintenance"
    )
    rearm_calls = require_calls(data, profile["rearm"], profile["rearm_calls"], "event rearm")
    exit_calls = require_calls(data, profile["exit"], profile["exit_calls"], "exit machine")
    rearm_refs = require_refs(
        data, profile["rearm"][0], profile["rearm_refs"], "event rearm"
    )
    exit_refs = require_refs(data, profile["exit"][0], profile["exit_refs"], "exit machine")
    local_refs = require_refs(data, local_start, profile["local_refs"], "local mode")

    forbidden_completion_calls = {
        local_start,
        profile["local_calls"][0],
        profile["local_calls"][1],
        profile["exit"][0],
    }
    if forbidden_completion_calls & set(completion_calls):
        raise ValueError("successful completion unexpectedly exits or cleans up PC mode")

    tables = {}
    for mode, address in profile["mode_tables"].items():
        raw = data[file_offset(address):file_offset(address) + 10]
        tables[mode] = {"address": f"0x{address:x}", "sha256": hashlib.sha256(raw).hexdigest()}

    return {
        "source": source_name,
        "image": {
            "model": profile["model"],
            "version": profile["version"],
            "size": len(data),
            "sha256": digest,
        },
        "display_local_pc_mode": {
            "handler": f"0x{local_start:x}",
            "accepted_modes": [0, 1, 4, 5],
            "secure_tables": tables,
            "call_targets": [f"0x{target:x}" for target in local_calls],
        },
        "successful_completion": {
            "handler": f"0x{profile['completion'][0]:x}",
            "stores_requested_mode": True,
            "stores_completion_flag": True,
            "stores_application_slot": True,
            "call_targets": [f"0x{target:x}" for target in completion_calls],
            "immediate_mode0_exit_or_cleanup": False,
        },
        "topology_maintenance": {
            "post_request_helper": f"0x{profile['post'][0]:x}",
            "clears_periodic_trigger": True,
            "clears_phase_bytes_4_and_5": True,
            "clears_phase_byte_3": profile["clears_phase_byte_3"],
            "post_request_call_targets": [f"0x{target:x}" for target in post_calls],
            "periodic_tick": f"0x{profile['periodic'][0]:x}",
            "periodic_rule": "invoke exit machine only while trigger byte +0x06 equals 1",
            "periodic_call_targets": [f"0x{target:x}" for target in periodic_calls],
            "event_rearm_call_targets": [f"0x{target:x}" for target in rearm_calls],
            "exit_machine_call_targets": [f"0x{target:x}" for target in exit_calls],
            "whole_image_rearm_references": [f"0x{address:x}" for address in rearm_refs],
            "whole_image_exit_references": [f"0x{address:x}" for address in exit_refs],
            "whole_image_local_mode_references": [f"0x{address:x}" for address in local_refs],
        },
        "conclusion": (
            "display-owned mode 4/5, retained successful completion, and trigger-disarmed "
            "maintenance already exist in this version"
        ),
        "limitations": [
            "static result for this exact display image only",
            "does not prove the absence of asynchronous topology events",
            "does not set or explain the motor's separate A0-created destination gate",
            "does not prove a destination write, persistence, or assistance cutoff",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("images", type=Path, nargs="+")
    args = parser.parse_args()
    try:
        results = [inspect(path.read_bytes(), path.name) for path in args.images]
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")
    print(json.dumps(results[0] if len(results) == 1 else results, indent=2))


if __name__ == "__main__":
    main()
