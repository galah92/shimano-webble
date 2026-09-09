#!/usr/bin/env python3
"""Offline E5000 M payload and checksum-window analysis; no device operations."""
import argparse
import json
from pathlib import Path
from inspect_firmware import inspect

BLOCK_BYTES = 64
WINDOW_BYTES = 1024
BASE_ADDRESS = 0xfc0000
MAX_M_BYTES = 0x1000000 - BASE_ADDRESS  # Do not wrap the observed 24-bit address field.


def window(length, offset):
    """Geometry corresponding to Q9.d for the E5000 default 1024-byte window.

    This identifies a checksum window, not permission to retry or resume a flash.
    """
    if not 0 < length <= MAX_M_BYTES or not 0 <= offset < length:
        raise ValueError('Offset or image length outside modeled M range')
    start = offset // WINDOW_BYTES * WINDOW_BYTES
    end = min(length, start + WINDOW_BYTES)
    return dict(start=start, end=end, first_block=start // 64 + 1,
                last_block=(end - 1) // 64 + 1, block_count=(end - start + 63) // 64,
                number=start // WINDOW_BYTES + 1, total=(length + 1023) // 1024)


def block_payload(data, offset, sequence):
    """Encode a block for an explicitly supplied sequence; no sequence scheduler.

    C0776xk.j1/M0: zero padding; 11 normally, 12 with a window checksum.
    A checksum value of zero still requires type 12.
    """
    w = window(len(data), offset)
    if offset % BLOCK_BYTES or not isinstance(sequence, int) or not 0 <= sequence <= 255:
        raise ValueError('Expected aligned offset and unsigned sequence byte')
    end = min(len(data), offset + BLOCK_BYTES)
    checkpoint = end == w['end']
    checksum = sum(data[w['start']:end]) & 255 if checkpoint else None
    payload = bytes([sequence, 0x12 if checkpoint else 0x11, 0])
    payload += data[offset:end].ljust(BLOCK_BYTES, b'\x00')
    if checkpoint:
        payload += bytes([checksum, 0, 0])
    return payload, checksum


def plan(data):
    header = inspect(data)
    if header['component'] != 'M':
        raise ValueError('D transfer is a separate protocol')
    window(len(data), 0)  # Validate address range before planning.
    checks = []
    for start in range(0, len(data), WINDOW_BYTES):
        end = min(len(data), start + WINDOW_BYTES)
        checks.append(dict(start=start, end=end, address=BASE_ADDRESS + start,
                           checksum=sum(data[start:end]) & 255))
    count = (len(data) + 63) // 64
    return dict(image=header, block_count=count, final_zero_padding_bytes=count * 64 - len(data),
                ordinary_data_write_bytes=68, checkpoint_data_write_bytes=71,
                checkpoint_count=len(checks), checksum_windows=checks,
                finish_checksum=sum(data) & 255, installable=False,
                unresolved=['exact preparation component pair and authenticity',
                            'reply classification and device progress semantics',
                            'sequence scheduling and conditional retries',
                            'power-loss recovery and paired finalization'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file', type=Path)
    args = parser.parse_args()
    try:
        with args.file.open('rb') as f:
            data = f.read(MAX_M_BYTES + 1)
        result = plan(data)
    except (OSError, ValueError) as error:
        parser.exit(1, f'{error}\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
