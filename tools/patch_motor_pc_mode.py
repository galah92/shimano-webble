#!/usr/bin/env python3
"""Build a minimal, reviewable D4.5.0 PC-mode-gate experiment.

The vendor image is supplied by the operator and stays outside Git.  By
default this tool only validates the exact recorded raw image and prints the
prospective two-site patch.  ``--output`` writes a new file without modifying
the input or overwriting an existing path.

The patch replaces the final ``BNE error`` in the A0 and A8 active-PC-mode
checks with Thumb NOPs.  It also changes only the header build byte from
4.5.0.0 to 4.5.0.1, giving reconnect readback a way to distinguish the
experimental image from restored stock.  It deliberately preserves A0's
zero-target check, A0's creation of the one-shot gate, A8's check and
consumption of that gate, and the persistent-record helper.  It is static
construction evidence only, not proof that a bootloader will accept the image
or that the bike will boot it.
"""

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path


LOAD_BASE = 0x10000


@dataclass(frozen=True)
class PatchSite:
    name: str
    address: int
    original: bytes
    replacement: bytes


@dataclass(frozen=True)
class PatchProfile:
    name: str
    size: int
    sha256: str
    sites: tuple[PatchSite, ...]


D450_PROFILE = PatchProfile(
    name="DU-E5000 D4.5.0 raw",
    size=138_072,
    sha256="44806bd54aedff95a88bb73fafe0f0581297f2f67b2ea35545cea012899d90bb",
    sites=(
        PatchSite("readback build marker 4.5.0.0 to 4.5.0.1", 0x10012, bytes.fromhex("00"), bytes.fromhex("01")),
        PatchSite("A0 active-PC-mode rejection", 0x252C8, bytes.fromhex("2dd1"), bytes.fromhex("00bf")),
        PatchSite("A8 active-PC-mode rejection", 0x25394, bytes.fromhex("24d1"), bytes.fromhex("00bf")),
    ),
)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def finish_checksum(data: bytes) -> int:
    return sum(data) & 0xFF


def patch_image(data: bytes, profile: PatchProfile, *, require_fingerprint: bool = True):
    if len(data) != profile.size:
        raise ValueError(f"expected {profile.size} bytes, got {len(data)}")
    original_hash = digest(data)
    if require_fingerprint and original_hash != profile.sha256:
        raise ValueError("input is not the exact recorded raw D4.5.0 image")

    changed = bytearray(data)
    sites = []
    for site in profile.sites:
        offset = site.address - LOAD_BASE
        if len(site.original) != len(site.replacement):
            raise ValueError(f"{site.name}: replacement changes image geometry")
        if offset < 0 or offset + len(site.original) > len(changed):
            raise ValueError(f"{site.name}: patch address is outside the image")
        actual = bytes(changed[offset:offset + len(site.original)])
        if actual != site.original:
            raise ValueError(f"{site.name}: expected instruction bytes are absent")
        changed[offset:offset + len(site.replacement)] = site.replacement
        sites.append({
            "name": site.name,
            "address": f"0x{site.address:x}",
            "file_offset": f"0x{offset:x}",
            "original": site.original.hex(),
            "replacement": site.replacement.hex(),
        })

    patched = bytes(changed)
    differences = [index for index, pair in enumerate(zip(data, patched)) if pair[0] != pair[1]]
    expected_differences = sorted(
        site.address - LOAD_BASE + index
        for site in profile.sites
        for index, pair in enumerate(zip(site.original, site.replacement))
        if pair[0] != pair[1]
    )
    if differences != expected_differences:
        raise ValueError("patched image differs outside the declared instruction bytes")

    report = {
        "profile": profile.name,
        "size": len(data),
        "input_sha256": original_hash,
        "input_finish_checksum": f"0x{finish_checksum(data):02x}",
        "output_sha256": digest(patched),
        "output_finish_checksum": f"0x{finish_checksum(patched):02x}",
        "changed_bytes": len(differences),
        "sites": sites,
        "preserved_guards": [
            "A0 target byte must still be zero",
            "A0 must still create the one-shot destination gate",
            "A8 must still observe and consume that gate",
            "A8 still calls the original persistent-record helper",
        ],
        "readback_version": "4.5.0.1",
        "limitations": [
            "no modified image has been sent to a bike",
            "bootloader acceptance is not established by static construction",
            "successful boot, destination persistence, and assistance speed are unverified",
        ],
    }
    return patched, report


def self_test():
    profile = PatchProfile(
        name="synthetic",
        size=32,
        sha256="unused",
        sites=(
            PatchSite("first", LOAD_BASE + 4, bytes.fromhex("2dd1"), bytes.fromhex("00bf")),
            PatchSite("second", LOAD_BASE + 20, bytes.fromhex("24d1"), bytes.fromhex("00bf")),
        ),
    )
    sample = bytearray(range(profile.size))
    for site in profile.sites:
        offset = site.address - LOAD_BASE
        sample[offset:offset + len(site.original)] = site.original
    patched, report = patch_image(bytes(sample), profile, require_fingerprint=False)
    assert report["changed_bytes"] == 4
    assert patched[:4] == bytes(sample[:4]) and patched[6:20] == bytes(sample[6:20])
    assert patched[22:] == bytes(sample[22:])
    assert patched[4:6] == bytes.fromhex("00bf") and patched[20:22] == bytes.fromhex("00bf")
    damaged = bytearray(sample)
    damaged[4] ^= 1
    try:
        patch_image(bytes(damaged), profile, require_fingerprint=False)
    except ValueError as error:
        assert "expected instruction bytes" in str(error)
    else:
        raise AssertionError("modified input was not rejected")
    return {"self_test": "passed", "changed_bytes": report["changed_bytes"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path, nargs="?", help="exact raw D4.5.0 image")
    parser.add_argument("--output", type=Path, help="write the patched image to a new explicit path")
    parser.add_argument("--self-test", action="store_true", help="run without vendor data")
    args = parser.parse_args()

    if args.self_test:
        if args.image or args.output:
            parser.error("--self-test does not accept an image or output")
        print(json.dumps(self_test(), indent=2))
        return
    if args.image is None:
        parser.error("image is required unless --self-test is used")

    try:
        data = args.image.read_bytes()
        patched, report = patch_image(data, D450_PROFILE)
        if args.output:
            if args.output.exists():
                raise ValueError(f"refusing to overwrite {args.output}")
            args.output.write_bytes(patched)
            report["output"] = str(args.output)
        else:
            report["output"] = None
            report["dry_run"] = True
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
