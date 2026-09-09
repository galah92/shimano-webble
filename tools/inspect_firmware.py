#!/usr/bin/env python3
"""Read-only E5000 raw DAT header inspection. Does not authorize a firmware update."""
import argparse
import hashlib
import json
from pathlib import Path

MAX_BYTES = 32 * 1024 * 1024

def version(data, offset):
    packed, patch, build = data[offset:offset + 3]
    major, minor = packed >> 4, packed & 15
    if major != 4 or minor > 9 or patch == 255 or build == 255:
        return None
    return f'{major}.{minor}.{patch}.{build}'

def inspect(data):
    if not 256 <= len(data) <= MAX_BYTES:
        raise ValueError('Expected a complete raw DAT between 256 bytes and 32 MiB')
    # Oa.B / Ja.a: family 0x22; two distinct header layouts.
    candidates = []
    if data[:16] == b'\xff' * 16 and data[40:43] == bytes([0x22, 0, 4]):
        if v := version(data, 16):
            candidates.append(('D', v))
    if data[12:16] == bytes([255, 255, 0x22, 0]):
        if v := version(data, 8):
            candidates.append(('M', v))
    if len(candidates) != 1:
        raise ValueError('Unrecognized or ambiguous raw E5000 header; wrapped/encrypted assets are not supported')
    component, v = candidates[0]
    return dict(family='E5000/E50X0', component=component, version=v,
                size=len(data), sha256=hashlib.sha256(data).hexdigest(),
                validation='header classification only; authenticity, completeness and bike compatibility unverified')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('files', type=Path, nargs='+')
    args = parser.parse_args()
    results = []
    for path in args.files:
        try:
            with path.open('rb') as f:
                data = f.read(MAX_BYTES + 1)
            results.append(dict(file=str(path), **inspect(data)))
        except (OSError, ValueError) as error:
            parser.exit(1, f'{path}: {error}\n')
    print(json.dumps(results, indent=2))

if __name__ == '__main__':
    main()
