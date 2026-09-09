#!/usr/bin/env python3
"""Offline E5000 D transfer arithmetic. No Bluetooth, upload, or update authorization."""
import argparse
import hashlib
import json
from pathlib import Path
from inspect_firmware import inspect

BLOCK_BYTES = 64
BANK_BYTES = 65536
MAX_D_BYTES = 3 * BANK_BYTES  # Only the three banks seen in the E5000 branch are modeled.


def block_payload(data, index, sequence):
    """Return the 70-byte inner data payload and unpadded checksum contribution.

    eTuning C0041b7 Q1/M1; the updater adds command 0B for 2AFA transport.
    This is encoding only: it does not implement reply parsing or retries.
    """
    if not 0 < len(data) <= MAX_D_BYTES:
        raise ValueError('D image size outside modeled three-bank range')
    if not isinstance(index, int) or not 0 <= index < (len(data) + 63) // 64:
        raise ValueError('Block index outside image')
    if not isinstance(sequence, int) or not 0 <= sequence <= 255:
        raise ValueError('Sequence must be an unsigned byte')
    chunk = data[index * BLOCK_BYTES:(index + 1) * BLOCK_BYTES]
    padded = chunk.ljust(BLOCK_BYTES, b'\xff')
    payload = bytes([sequence, 2, 0]) + padded + bytes([sum(padded) & 255]) + index.to_bytes(2, 'little')
    return payload, sum(chunk) & 255


def plan(data):
    """Summarize a no-retry D transfer without emitting firmware or write commands."""
    header = inspect(data)
    if header['component'] != 'D':
        raise ValueError('M transfer is a separate protocol and is not modeled')
    if len(data) > MAX_D_BYTES:
        raise ValueError('D image exceeds modeled three-bank range')
    count = (len(data) + BLOCK_BYTES - 1) // BLOCK_BYTES
    padded_sum = 0
    image_sum = 0
    frame_digest = hashlib.sha256()
    for index in range(count):
        # A data frame and its query each consume one sequence number.
        payload, contribution = block_payload(data, index, (2 * index) & 255)
        frame_digest.update(bytes([0x0b]) + payload)
        padded_sum = (padded_sum + payload[67]) & 255
        image_sum = (image_sum + contribution) & 255
    return dict(image=header, block_count=count, final_padding_bytes=count * BLOCK_BYTES - len(data),
                padded_checksum=padded_sum, finish_checksum=image_sum,
                data_write_bytes=71, data_and_query_count_without_retries=count * 2,
                start_page_index=(len(data) - 1) // 2048,
                bank_boundaries=[dict(block_index=i, bank=i // 1024, address=0x4000 + i * 64)
                                 for i in range(0, count, 1024)],
                no_retry_data_frames_sha256=frame_digest.hexdigest(),
                installable=False,
                unresolved=['firmware authenticity and preparation suitability',
                            'update entry and actual BLE long-write behavior',
                            'reply correlation, retry and recovery behavior',
                            'M component transfer and pair finalization'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file', type=Path)
    args = parser.parse_args()
    try:
        with args.file.open('rb') as f:
            data = f.read(MAX_D_BYTES + 1)
        result = plan(data)
    except (OSError, ValueError) as error:
        parser.exit(1, f'{error}\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
