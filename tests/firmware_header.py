"""Synthetic firmware headers. No vendor firmware is included."""
import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from inspect_firmware import inspect

class FirmwareHeaderTests(unittest.TestCase):
    def sample(self, component):
        data = bytearray(256)
        if component == 'D':
            data[:16] = b'\xff' * 16
            data[16:19] = bytes([0x43, 0, 0])
            data[40:43] = bytes([0x22, 0, 4])
        else:
            data[8:11] = bytes([0x43, 0, 1])
            data[12:16] = bytes([255,255,0x22,0])
        return data

    def test_components_have_distinct_version_offsets(self):
        for component, expected in [('D','4.3.0.0'), ('M','4.3.0.1')]:
            result = inspect(self.sample(component))
            self.assertEqual(result['component'], component)
            self.assertEqual(result['version'], expected)
            self.assertIn('compatibility unverified', result['validation'])

    def test_wrong_family_short_or_invalid_version_rejected(self):
        for component, offset, version_offset in [('D',40,16),('M',14,8)]:
            data = self.sample(component)
            with self.assertRaises(ValueError): inspect(data[:128])
            data[offset] = 0x21  # E7000 must not be classified as E5000.
            with self.assertRaises(ValueError): inspect(data)
            data = self.sample(component)
            data[version_offset] = 0x4a
            with self.assertRaises(ValueError): inspect(data)
            data[version_offset] = 0x43
            data[version_offset + 2] = 255
            with self.assertRaises(ValueError): inspect(data)

    def test_mutation_changes_digest_without_proving_integrity(self):
        data = self.sample('D'); before = inspect(data)
        data[-1] ^= 1; after = inspect(data)
        self.assertNotEqual(before['sha256'], after['sha256'])
        self.assertEqual(before['version'], after['version'])
        self.assertIn('completeness', after['validation'])

if __name__ == '__main__': unittest.main()
