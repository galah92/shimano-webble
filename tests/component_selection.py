"""Selection cases derived from Th.v3/Mh.l; synthetic headers only."""
import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from compare_components import compare, plan


def images():
    d, m = bytearray(256), bytearray(256)
    d[:16] = b'\xff' * 16
    d[16:19] = bytes([0x43, 0, 0])
    d[40:43] = bytes([34, 0, 4])
    m[8:11] = bytes([0x42, 1, 0])
    m[12:16] = bytes([255, 255, 34, 0])
    return d, m


class ComponentSelectionTests(unittest.TestCase):
    def test_independent_versions_and_order(self):
        for d, m, order in [('4.5.0.0', '4.2.1.0', ['D']),
                            ('4.3.0.0', '4.1.0.0', ['M']),
                            ('4.5.0.0', '4.4.3.0', ['M', 'D']),
                            ('4.5.0.0', '4.4.8.0', ['M', 'D']),
                            ('4.3.0.0', '4.2.1.0', [])]:
            result = plan(*images(), d, m)
            self.assertEqual(result['normal_mode_order'], order)
            self.assertFalse(result['installable'])

    def test_unknown_and_recovery_do_not_produce_order(self):
        for d, m in [(None, None), ('4.5.0.0', None), ('4.15.0.0', '4.2.1.0')]:
            self.assertIsNone(plan(*images(), d, m)['normal_mode_order'])

    def test_full_version_and_bad_input(self):
        self.assertEqual(compare('4.3.0.0', '4.3.0.1'), 'downgrade')
        self.assertEqual(compare('4.3.0.1', '4.3.0.0'), 'upgrade')
        for value in ('4.5.0', '4.5.0.-1', '4.5.256.0', 'x.0.0.0'):
            with self.assertRaises(ValueError): compare('4.3.0.0', value)
        with self.assertRaises(ValueError): plan(*reversed(images()))


if __name__ == '__main__':
    unittest.main()
