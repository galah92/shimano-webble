"""Synthetic M codec vectors and window boundary tests; no vendor firmware."""
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from plan_m_transfer import block_payload, window, plan, MAX_M_BYTES


def image(size):
    data = bytearray((i * 37 + 11) & 255 for i in range(size))
    data[8:11] = bytes([0x42, 1, 0])
    data[12:16] = bytes([255, 255, 34, 0])
    return bytes(data)


class MTransferTests(unittest.TestCase):
    def test_java_payload_and_window_vectors(self):
        vectors = json.loads(Path(__file__).with_name('m_transfer_vectors.json').read_text())
        for v in vectors:
            with self.subTest(length=v['length'], offset=v['offset']):
                data = bytes((i * 37 + 11) & 255 for i in range(v['length']))
                payload, checksum = block_payload(data, v['offset'], v['sequence'])
                self.assertEqual(payload.hex(), v['payload_hex'])
                self.assertEqual(checksum, v['checksum'])
                self.assertEqual(list(window(len(data), v['offset']).values()), v['window'])

    def test_zero_checksum_is_present(self):
        payload, checksum = block_payload(bytes(64), 0, 255)
        self.assertEqual(checksum, 0)
        self.assertEqual(payload[:3], bytes([255, 18, 0]))
        self.assertEqual(len(payload), 70)

    def test_reassembly_and_window_partition(self):
        for size in (256, 1023, 1024, 1025, 2048, 2049, MAX_M_BYTES):
            with self.subTest(size=size):
                data = image(size)
                result = plan(data)
                rebuilt = bytearray()
                checks = []
                for offset in range(0, size, 64):
                    payload, checksum = block_payload(data, offset, (offset // 64) % 256)
                    rebuilt += payload[3:67]
                    if checksum is not None:
                        checks.append(checksum)
                self.assertEqual(rebuilt[:size], data)
                self.assertEqual(rebuilt[size:], bytes(result['final_zero_padding_bytes']))
                self.assertEqual(checks, [w['checksum'] for w in result['checksum_windows']])
                self.assertEqual(sum(checks) % 256, result['finish_checksum'])
                self.assertEqual(result['checksum_windows'][-1]['end'], size)
                self.assertFalse(result['installable'])

    def test_invalid_inputs(self):
        for size, offset in ((0, 0), (64, -1), (64, 64), (MAX_M_BYTES + 1, 0)):
            with self.assertRaises(ValueError):
                window(size, offset)
        for offset, seq in ((1, 0), (0, -1), (0, 256)):
            with self.assertRaises(ValueError):
                block_payload(bytes(64), offset, seq)
        d = bytearray(256)
        d[:16] = b'\xff' * 16
        d[16:19] = bytes([0x43, 0, 0])
        d[40:43] = bytes([34, 0, 4])
        with self.assertRaisesRegex(ValueError, 'separate protocol'):
            plan(d)


if __name__ == '__main__':
    unittest.main()
