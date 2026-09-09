"""Golden fixtures from Hn.E plus F1 corrected against raw instructions, not live bootloader RX."""
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from d_command_reply import first_match


class CommandReplyTests(unittest.TestCase):
    def test_java_first_match_vectors(self):
        vectors = json.loads(Path(__file__).with_name('d_command_vectors.json').read_text())
        for case in vectors:
            with self.subTest(raw=case['raw']):
                result = first_match(bytes.fromhex(case['raw']))
                self.assertEqual(None if result is None else result.hex(), case['match'])

    def test_indexed_block_result_cannot_match_command_listener(self):
        # Both prefix and stripped payload must reject indexed data results.
        self.assertIsNone(first_match(bytes.fromhex('88310100')))
        self.assertIsNone(first_match(bytes.fromhex('88320100')))
        self.assertEqual(first_match(bytes.fromhex('88310000')), bytes.fromhex('88310000'))


if __name__ == '__main__': unittest.main()
