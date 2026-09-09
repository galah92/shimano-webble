"""Offline transfer vectors from extracted Java Q1/M1/S1; synthetic bytes only."""
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from plan_d_transfer import block_payload, plan, MAX_D_BYTES


def image(size):
    data = bytearray((i * 37 + 11) & 255 for i in range(size))
    data[:16] = b'\xff' * 16
    data[16:19] = bytes([0x43, 0, 0])
    data[40:43] = bytes([0x22, 0, 4])
    return bytes(data)


class TransferTests(unittest.TestCase):
    def test_java_oracle_vectors(self):
        vectors = json.loads(Path(__file__).with_name('transfer_vectors.json').read_text())
        for v in vectors:
            with self.subTest(length=v['length'], index=v['index'], sequence=v['sequence']):
                data = bytes((i * 37 + 11) & 255 for i in range(v['length']))
                payload, contribution = block_payload(data, v['index'], v['sequence'])
                self.assertEqual(payload.hex(), v['payload_hex'])
                self.assertEqual(payload[67], v['block_sum'])
                self.assertEqual(contribution, v['image_sum_part'])
                self.assertEqual(0x4000 + v['index'] * 64, v['address'])

    def test_checksum_excludes_padding_and_banks_cover_image(self):
        for size in (256, 257, 65536, 65537, 131072, 131073, MAX_D_BYTES):
            with self.subTest(size=size):
                data = image(size)
                result = plan(data)
                self.assertEqual(result['finish_checksum'], sum(data) % 256)
                self.assertEqual(result['padded_checksum'], (sum(data) + 255 * result['final_padding_bytes']) % 256)
                self.assertEqual(result['block_count'], (size + 63) // 64)
                self.assertEqual(len(result['bank_boundaries']), (size + 65535) // 65536)
                self.assertFalse(result['installable'])
                self.assertEqual(result['image']['version'], '4.3.0.0')
                # Reassemble payloads, checking counter wrap and exact image bytes.
                rebuilt = bytearray()
                for i in range(result['block_count']):
                    payload, _ = block_payload(data, i, (i * 2) % 256)
                    self.assertEqual(payload[0], (i * 2) % 256)
                    self.assertEqual(int.from_bytes(payload[68:70], 'little'), i)
                    rebuilt.extend(payload[3:67])
                self.assertEqual(rebuilt[:size], data)
                self.assertEqual(rebuilt[size:], b'\xff' * result['final_padding_bytes'])

    def test_rejects_unmodeled_inputs(self):
        for data in (b'', image(MAX_D_BYTES + 1), bytes(256)):
            with self.assertRaises(ValueError):
                plan(data)
        motor_m = bytearray(256)
        motor_m[8:11] = bytes([0x43, 0, 0])
        motor_m[12:16] = bytes([255, 255, 34, 0])
        with self.assertRaisesRegex(ValueError, 'separate protocol'):
            plan(motor_m)
        for index, seq in ((-1, 0), (4, 0), (0, -1), (0, 256)):
            with self.assertRaises(ValueError):
                block_payload(image(256), index, seq)


if __name__ == '__main__':
    unittest.main()
