"""Offline classification of already-normalized E5000 M reply envelopes.

Inputs are Dn protocol/payload fields, not raw GATT notifications. No framing,
timers, retries, device operations or permission to continue a flash are modeled.
"""


def classify(protocol, payload, query_sequence, data_sequence, checkpoint=False):
    for value in (protocol, query_sequence, data_sequence):
        if not isinstance(value, int) or not 0 <= value <= 255:
            raise ValueError('Expected unsigned protocol and sequence bytes')
    events = []
    # C0644tk with C0776xk.L0/n1. Preserve the source mask, not protocol equality.
    if protocol & 0x0b == 0x0b:
        if len(payload) > 3 and payload[1] == 0x83 and payload[2] == query_sequence:
            events.append(('query_status', payload[3]))
        if len(payload) > 2:
            opcode, sequence = payload[1:3]
            if opcode in (0x91, 0x92):
                events.append(('data_status' if sequence == data_sequence else 'other_data_status', opcode))
            if opcode == 0xc0:
                events.append(('data_ack' if sequence == data_sequence else 'other_data_ack', sequence))
    # Non-EP C0776xk.e1 scans the normalized payload for the first F2 00 marker.
    # It has no sequence correlation: this fact must survive into future design.
    if checkpoint:
        for i in range(len(payload) - 2):
            if payload[i:i + 2] == b'\xf2\x00':
                status = payload[i + 2]
                if status in (0x31, 0x32):
                    events.append(('uncorrelated_checksum_status', status))
                break
    return events
