"""Synthetic parser/dispatch tests; contains no vendor image or bike transport."""
import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from inspect_radio_candidate import decode_hex, inspect, serial_receive_route


def record(kind, address=0, payload=b''):
    data = bytes([len(payload)]) + address.to_bytes(2, 'big') + bytes([kind]) + payload
    return ':' + (data + bytes([-sum(data) & 255])).hex()


def hex_file(*records):
    return ('\n'.join(records) + '\n').encode('ascii')


class RadioCandidateTests(unittest.TestCase):
    def test_valid_records(self):
        data = hex_file(record(4, payload=b'\x00\x01'),
                        record(0, 0xD000, b'\x12\x34'), record(1))
        self.assertEqual(decode_hex(data), {0x1D000: 0x12, 0x1D001: 0x34})

    def test_malformed_records_fail_closed(self):
        prefix = record(4, payload=b'\x00\x01')
        entry = record(0, 0xD000, b'\x12\x34')
        for records in [(prefix, entry), (prefix, entry, entry, record(1)),
                        (prefix, record(0, 0xCFFF, b'\x01'), record(1)),
                        (prefix, entry, record(1), record(1)),
                        (prefix, entry[:-2] + '00', record(1)),
                        (prefix, record(2, payload=b'\x00\x00'), record(1))]:
            with self.subTest(records=records), self.assertRaises(ValueError):
                decode_hex(hex_file(*records))

    def test_wrong_image_is_not_inspected(self):
        for data in (b'', b':00000001FF\n', bytes(125032)):
            with self.subTest(size=len(data)), self.assertRaises(ValueError):
                inspect(data)

    def test_bounded_dispatch_all_byte_values(self):
        # Own fixture: CMP r3,91; BEQ 1e750; B 1e752. No vendor bytes.
        data = struct.pack('<HHH', 0x2B91, 0xD05E, 0xE05E)
        memory = {0x1E68E + offset: value for offset, value in enumerate(data)}
        for value in range(256):
            self.assertEqual(serial_receive_route(memory, value),
                             0x1E750 if value == 0x91 else 0x1E752)

    def test_missing_or_unexpected_dispatch_rejected(self):
        for memory in ({}, {0x1E68E: 0, 0x1E68F: 0}):
            with self.subTest(memory=memory), self.assertRaises(ValueError):
                serial_receive_route(memory, 0x91)
        for value in (-1, 256):
            with self.subTest(value=value), self.assertRaises(ValueError):
                serial_receive_route({}, value)


if __name__ == '__main__':
    unittest.main()
