#!/usr/bin/env python3
"""Verify the SC-E7000 4.1.0 display-owned PC-mode path without dumping firmware.

The vendor image stays outside Git. This read-only tool accepts the exact
plaintext image recorded in ASSETS.md, verifies its fingerprint, and reports
the bounded control-flow facts used by the display-owned protected-mode build.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path

LOAD_BASE = 0x10000
EXPECTED_SIZE = 126_508
EXPECTED_SHA256 = "1f3c42ad0cc3e46d2e9affd5f023245f645acbc1c8ee3d68569bfcb25c9c3e79"


def file_offset(address):
    return address - LOAD_BASE


def require_bytes(data, address, expected, label):
    actual = data[file_offset(address):file_offset(address) + len(expected)]
    if actual != expected:
        raise ValueError(f"{label} signature mismatch at 0x{address:x}")


def thumb_bl_targets(data, start, end):
    """Decode direct Thumb-2 BL targets in a bounded, already identified handler."""
    targets = []
    for address in range(start, end - 3, 2):
        offset = file_offset(address)
        first, second = struct.unpack_from("<HH", data, offset)
        if first & 0xF800 != 0xF000 or second & 0xD000 != 0xD000:
            continue
        sign = (first >> 10) & 1
        imm10 = first & 0x03FF
        j1 = (second >> 13) & 1
        j2 = (second >> 11) & 1
        imm11 = second & 0x07FF
        i1 = 1 ^ (j1 ^ sign)
        i2 = 1 ^ (j2 ^ sign)
        immediate = (sign << 24) | (i1 << 23) | (i2 << 22) | (imm10 << 12) | (imm11 << 1)
        if sign:
            immediate -= 1 << 25
        targets.append(address + 4 + immediate)
    return targets


def thumb_bl_references(data, target):
    """Return all halfword-aligned direct Thumb-2 BL references to target."""
    references = []
    for address in range(LOAD_BASE, LOAD_BASE + len(data) - 3, 2):
        offset = file_offset(address)
        first, second = struct.unpack_from("<HH", data, offset)
        if first & 0xF800 != 0xF000 or second & 0xD000 != 0xD000:
            continue
        sign = (first >> 10) & 1
        imm10 = first & 0x03FF
        j1 = (second >> 13) & 1
        j2 = (second >> 11) & 1
        imm11 = second & 0x07FF
        i1 = 1 ^ (j1 ^ sign)
        i2 = 1 ^ (j2 ^ sign)
        immediate = (sign << 24) | (i1 << 23) | (i2 << 22) | (imm10 << 12) | (imm11 << 1)
        if sign:
            immediate -= 1 << 25
        if address + 4 + immediate == target:
            references.append(address)
    return references


def secure_table(data, address):
    table = data[file_offset(address):file_offset(address) + 10]
    return {
        "address": f"0x{address:x}",
        "word_count": 5,
        "sha256": hashlib.sha256(table).hexdigest(),
    }


def initialized_priority_table(data):
    """Decode the exact startup data block copied to RAM 0x2000000c."""
    source = file_offset(0x2EA74)
    end = source + 0x3B3
    position = source
    output = bytearray()
    while position < end:
        control = data[position]
        position += 1
        literal_count = control & 3
        if literal_count == 0:
            literal_count = data[position] + 3
            position += 1
        match_count = control >> 4
        if match_count == 15:
            match_count = data[position] + 15
            position += 1
        literal_size = literal_count - 1
        output.extend(data[position:position + literal_size])
        position += literal_size
        if match_count:
            distance_low = data[position]
            position += 1
            distance_high = (control >> 2) & 3
            if distance_high == 3:
                distance_high = data[position]
                position += 1
            distance = distance_low + 256 * distance_high
            if distance == 0 or distance > len(output):
                raise ValueError("Invalid display startup-data backreference")
            for _ in range(match_count + 2):
                output.append(output[-distance])
    if position != end or len(output) != 1764:
        raise ValueError("Display startup-data bounds mismatch")
    # RAM +0x0c..+0x27 is the 14-entry category/opcode priority table.
    table = bytes(output[12:40])
    if hashlib.sha256(table).hexdigest() != "8c4d154f1e7c3d9c6ec46b9033896f22fefd1f25ba8a263127a9fe9f420c4911":
        raise ValueError("Display queue priority table mismatch")
    return {(table[i], table[i + 1]) for i in range(0, len(table), 2)}


def inspect(data):
    digest = hashlib.sha256(data).hexdigest()
    if len(data) != EXPECTED_SIZE or digest != EXPECTED_SHA256:
        raise ValueError("Expected the exact plaintext SC-E7000 4.1.0 image recorded in ASSETS.md")

    # Pin the small state writes used by the semantic report. The full image
    # fingerprint above prevents these checks from silently matching a variant.
    require_bytes(data, 0x236FC, bytes.fromhex(
        "1cb5040005d0401e0dd0c01e01280ad915e0"),
        "display-local mode dispatch without active-mode short circuit")
    require_bytes(data, 0x212B4, bytes.fromhex("724de870"),
                  "unconditional requested-mode staging")
    require_bytes(data, 0x21CC2, bytes.fromhex("4748002181736170"), "explicit mode-0 state clear")
    require_bytes(data, 0x21D76, bytes.fromhex("1a4da9730020a0700120a8772078a874"),
                  "successful secure completion state update")
    require_bytes(data, 0x1F6F0, bytes.fromhex(
        "80b590480189002901d0491e01818079012801d100f097f801bd"),
        "periodic topology-maintenance gate")
    require_bytes(data, 0x1F7A4, bytes.fromhex(
        "80b563480021817101714171c170f9f78dfe01bd"),
        "post-request topology-maintenance disarm")
    require_bytes(data, 0x2DBCE, bytes.fromhex(
        "62782078102804d1a11c2800fff7f3fd32bd"),
        "type-10 full-copy forward branch")
    if struct.unpack_from("<I", data, file_offset(0x21DF8))[0] != 0x1232:
        raise ValueError("category-32 completion literal mismatch")

    local_calls = thumb_bl_targets(data, 0x236FC, 0x23746)
    mode_builder_calls = thumb_bl_targets(data, 0x212AC, 0x21470)
    display_queue_calls = thumb_bl_targets(data, 0x210C6, 0x21100)
    phone_queue_calls = thumb_bl_targets(data, 0x200BC, 0x200D8)
    priority_table = initialized_priority_table(data)
    expected_local_calls = [0x212AC, 0x17CFA, 0x17CC8, 0x212AC, 0x1F7A4]
    completion_calls = thumb_bl_targets(data, 0x21D2C, 0x21DDE)
    expected_completion_calls = [0x2118C, 0x2AC9A, 0x2C418, 0x23E14, 0x2AC3A,
                                 0x2ACCA, 0x2ACCA, 0x210C6, 0x19476]
    if local_calls != expected_local_calls:
        raise ValueError("display-local 0C call graph mismatch")
    if mode_builder_calls.count(0x210C6) != 6 or display_queue_calls != [0x2BF74]:
        raise ValueError("display-owned mode request/secure-word enqueue mismatch")
    if phone_queue_calls != [0x2BF74]:
        raise ValueError("phone-forwarded drive command enqueue mismatch")
    if {(0x32, 0x10), (0x32, 0x30), (0x16, 0xA0), (0x16, 0xAC)} & priority_table:
        raise ValueError("protected mode, A0, or AC unexpectedly uses the priority queue")
    if completion_calls != expected_completion_calls:
        raise ValueError("secure completion call graph mismatch")

    post_request_calls = thumb_bl_targets(data, 0x1F7A4, 0x1F7B8)
    periodic_calls = thumb_bl_targets(data, 0x1F6F0, 0x1F70A)
    topology_calls = thumb_bl_targets(data, 0x1F7B8, 0x1F816)
    maintenance_calls = thumb_bl_targets(data, 0x1F836, 0x1F8CE)
    enqueue_calls = thumb_bl_targets(data, 0x2BF74, 0x2C024)
    forward_selector_calls = thumb_bl_targets(data, 0x2DBB2, 0x2DC88)
    full_copy_calls = thumb_bl_targets(data, 0x2D7C4, 0x2D888)
    topology_rearm_references = thumb_bl_references(data, 0x1F7B8)
    maintenance_exit_references = thumb_bl_references(data, 0x1F836)
    local_mode_handler_references = thumb_bl_references(data, 0x236FC)
    if post_request_calls != [0x194D0]:
        raise ValueError("post-request maintenance-disarm call graph mismatch")
    if periodic_calls != [0x1F836]:
        raise ValueError("periodic maintenance call graph mismatch")
    if topology_calls != [0x234A2, 0x1F81C, 0x194DE, 0x234AE, 0x234E2,
                          0x23508, 0x1F836, 0x234E2, 0x23508, 0x236FC]:
        raise ValueError("topology-event call graph mismatch")
    if maintenance_calls != [0x234AE, 0x236FC, 0x1F8CE, 0x1F81C, 0x1F8CE,
                             0x1F76C, 0x201E2]:
        raise ValueError("topology-maintenance state-machine call graph mismatch")
    if enqueue_calls != [0x2BC54, 0x2E580, 0x2D53A, 0x2DBB2, 0x2DF7A, 0x2BC88]:
        raise ValueError("drive-command enqueue call graph mismatch")
    if forward_selector_calls != [0x2D7C4, 0x2D75E, 0x2D6B4, 0x2D6B4,
                                  0x2D6B4, 0x2D6B4, 0x2D718, 0x2D718,
                                  0x2D718, 0x2D718]:
        raise ValueError("drive-command forward-selector call graph mismatch")
    if full_copy_calls:
        raise ValueError("full-copy formatter unexpectedly gained a direct call")
    if topology_rearm_references != [0x17820, 0x178A6, 0x17B6C, 0x18352]:
        raise ValueError("whole-image topology-rearm references mismatch")
    if maintenance_exit_references != [0x1F704, 0x1F7F0]:
        raise ValueError("whole-image maintenance-exit references mismatch")
    if local_mode_handler_references != [0x16210, 0x1F810, 0x1F85A]:
        raise ValueError("whole-image local-mode-handler references mismatch")

    forbidden_immediate_exit_targets = {0x236FC, 0x212AC, 0x17CFA, 0x1F76C}
    pc_mode_mutation_targets = forbidden_immediate_exit_targets | {0x1F7B8, 0x1F836}
    drive_forward_calls = enqueue_calls + forward_selector_calls + full_copy_calls
    return {
        "image": {
            "model": "SC-E7000",
            "version": "4.1.0",
            "size": len(data),
            "sha256": digest,
        },
        "display_local_0c": {
            "handler": "0x236fc",
            "accepted_modes": [0, 1, 4, 5],
            "mode_tables": {
                "1": secure_table(data, 0x21DFC),
                "4": secure_table(data, 0x21E08),
                "5": secure_table(data, 0x21E14),
            },
            "call_targets": [f"0x{target:x}" for target in local_calls],
            "same_accepted_mode_request_is_forwarded_again": True,
            "builder_stages_each_requested_mode_before_dispatch": True,
        },
        "five_word_completion": {
            "handler": "0x21d2c",
            "state_order": [
                "store requested mode at connection_state+0x0e",
                "set completion flag at connection_state+0x1e",
                "store application slot at connection_state+0x12",
                "construct category-32 opcode-12 completion",
            ],
            "call_targets": [f"0x{target:x}" for target in completion_calls],
            "immediate_mode0_or_cleanup_call": bool(forbidden_immediate_exit_targets & set(completion_calls)),
        },
        "topology_maintenance": {
            "post_nonzero_request_helper": "0x1f7a4",
            "post_request_state_writes": [
                "clear maintenance trigger at topology_state+0x06",
                "clear phase bytes at topology_state+0x04, +0x05, and +0x03",
            ],
            "periodic_tick": "0x1f6f0",
            "periodic_tick_rule": "call exit state machine 0x1f836 only when topology_state+0x06 equals 1",
            "periodic_tick_call_targets": [f"0x{target:x}" for target in periodic_calls],
            "event_rearm_handler": "0x1f7b8",
            "event_rearm_call_targets": [f"0x{target:x}" for target in topology_calls],
            "whole_image_event_rearm_references": [
                f"0x{reference:x}" for reference in topology_rearm_references
            ],
            "whole_image_exit_machine_references": [
                f"0x{reference:x}" for reference in maintenance_exit_references
            ],
            "whole_image_local_mode_handler_references": [
                f"0x{reference:x}" for reference in local_mode_handler_references
            ],
            "exit_state_machine_call_targets": [f"0x{target:x}" for target in maintenance_calls],
            "mode0_call_sites": ["0x1f810", "0x1f85a"],
            "timer_only_exit_while_trigger_remains_clear": False,
        },
        "drive_command_forward": {
            "enqueue": "0x2bf74",
            "type_0x10_selector": "0x2dbb2",
            "full_copy_formatter": "0x2d7c4",
            "enqueue_call_targets": [f"0x{target:x}" for target in enqueue_calls],
            "selector_call_targets": [f"0x{target:x}" for target in forward_selector_calls],
            "full_copy_call_targets": [f"0x{target:x}" for target in full_copy_calls],
            "direct_pc_mode_rearm_exit_or_cleanup_call": bool(
                pc_mode_mutation_targets & set(drive_forward_calls)
            ),
        },
        "early_queue_candidate": {
            "local_0c_queues_mode_request_and_five_words_before_2c_ack": True,
            "mode_packets_and_phone_a0_share_enqueue": "0x2bf74",
            "mode_a0_and_ac_absent_from_priority_table": True,
            "normal_bus_ring_enqueue": "0x2d7c4",
            "normal_bus_ring_dequeue": "0x2d61e",
            "candidate": "enqueue one unchanged A0 after display 2C 00 but before motor mode-5 completion",
            "bike_acceptance": "unverified; do not repeat the journaled attempt",
        },
        "conclusion": (
            "successful display-owned completion records the requested mode with no immediate exit; "
            "the post-request helper also disarms periodic topology maintenance, so a "
            "later mode-0 exit requires a fresh event to re-arm that state machine; the "
            "raw drive-command enqueue path does not synchronously re-arm or exit it"
        ),
        "limitations": [
            "static result for this exact display image only",
            "does not prove runtime bus ordering or queue state after the local acknowledgement",
            "does not prove that no topology or lifecycle event occurs before the next BLE write",
            "does not exclude an asynchronous event after a drive command is enqueued",
            "does not prove the motor accepts A0 or A8",
            "does not prove persistence or assistance cutoff",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path)
    args = parser.parse_args()
    try:
        with args.image.open("rb") as source:
            data = source.read(EXPECTED_SIZE + 1)
        result = inspect(data)
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
