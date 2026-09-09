"""Synthetic normalized envelopes; not live update traffic."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from m_reply import classify, envelopes, source_query_retryable
import json


class MReplyTests(unittest.TestCase):
    def test_source_retry_filter_is_narrow(self):
        for message in ('TRANSFER_START 83 error status=0x01',
                        'prefix TRANSFER_START_83_ERROR target=07 status=0x01 suffix'):
            self.assertTrue(source_query_retryable(message))
        for message in (None, '', 'timeout', 'checksum failed',
                        'TRANSFER_START_83_ERROR status=0x02',
                        'status=0x01', 'TRANSFER_START_83_ERROR'):
            self.assertFalse(source_query_retryable(message))

    def test_java_envelope_vectors(self):
        vectors = json.loads(Path(__file__).with_name('m_envelope_vectors.json').read_text())
        for vector in vectors:
            with self.subTest(raw=vector['raw']):
                actual = [[protocol, payload.hex()] for protocol, payload in envelopes(bytes.fromhex(vector['raw']))]
                self.assertEqual(actual, vector['envelopes'])

    def test_raw_and_escaped_ack_reach_same_classifier(self):
        for raw in ('0b00c007', '000b00c007', 'bb0b00c007d3bb'):
            events = [event for protocol, payload in envelopes(bytes.fromhex(raw))
                      for event in classify(protocol, payload, 8, 7)]
            self.assertEqual(events, [('data_ack', 7)])

    def test_query_and_data_sequences_are_distinct(self):
        self.assertEqual(classify(11, bytes([0,131,8,1]), 8,7), [('query_status',1)])
        self.assertEqual(classify(11, bytes([0,131,7,1]), 8,7), [])
        self.assertEqual(classify(11, bytes([0,192,7]), 8,7), [('data_ack',7)])
        self.assertEqual(classify(11, bytes([0,192,8]), 8,7), [('other_data_ack',8)])

    def test_data_status_is_not_ack(self):
        for opcode in (145,146):
            self.assertEqual(classify(11, bytes([0,opcode,7]), 8,7), [('data_status',opcode)])
            self.assertEqual(classify(11, bytes([0,opcode,6]), 8,7), [('other_data_status',opcode)])

    def test_checksum_has_no_sequence_and_uses_first_marker(self):
        for status in (49,50):
            payload=bytes([0,192,7,242,0,status])
            self.assertEqual(classify(11,payload,8,7,True), [('data_ack',7),('uncorrelated_checksum_status',status)])
            self.assertEqual(classify(11,payload,8,7,False), [('data_ack',7)])
        self.assertEqual(classify(0,bytes([242,0,49]),8,7,True), [('uncorrelated_checksum_status',49)])
        self.assertEqual(classify(11,bytes([242,0,0,242,0,49]),8,7,True), [])

    def test_protocol_mask_and_truncation(self):
        for protocol in (11,27,255):
            self.assertEqual(classify(protocol,bytes([0,192,7]),8,7), [('data_ack',7)])
        for protocol in (0,1,8,10):
            self.assertEqual(classify(protocol,bytes([0,192,7]),8,7), [])
        for payload in (b'',b'\x00',b'\x00\xc0',b'\x00\x83\x08',b'\xf2\x00'):
            self.assertEqual(classify(11,payload,8,7,True), [])
        with self.assertRaises(ValueError): classify(11,b'',256,7)


if __name__ == '__main__': unittest.main()
