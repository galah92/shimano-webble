"""Offline normalization and classification of E5000 M reply candidates.

envelopes() models Hn.K/C/J for one raw notification; classify() consumes its
Dn protocol/payload candidates. No reassembly, timers, retries, device operations
or permission to continue a flash are modeled.
"""


def envelopes(raw):
    """Hn.K/C/J candidate interpretations of one notification, not reassembly.

    Only the escaped candidate validates a checksum. Raw candidates survive a
    bad escaped checksum; callers must not mistake this for validated framing.
    """
    raw = bytes(raw)
    candidates = []

    def add(data):
        if not data:
            return
        protocol = data[0]
        if protocol == 0x48 and len(data) > 2:
            payload = data[2:]
        elif protocol == 0xf2 and len(data) >= 3:
            protocol, payload = 0x48, data
        else:
            payload = data[1:]
        candidates.append((protocol, payload))

    add(raw)
    if len(raw) > 1 and raw[0] == 0:
        add(raw[1:])
    if len(raw) < 3:
        return candidates
    frame = raw[1:] if raw[0] == 0 and len(raw) > 3 else raw
    if frame[-1] != 0xbb:
        return candidates
    decoded = bytearray()
    i = 1 if frame[0] == 0xbb else 0
    while i < len(frame) - 1:
        byte = frame[i]
        if byte == 0xbd and i + 1 < len(frame) - 1:
            i += 1
            byte = frame[i] ^ 0x20
        decoded.append(byte)
        i += 1
    if len(decoded) >= 2 and (sum(decoded[:-1]) + 1) & 255 == decoded[-1]:
        add(bytes(decoded[:-1]))
    return candidates


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
