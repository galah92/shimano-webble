"""Offline Hn.E/F1 first-match analysis. This does not authorize setup commands."""
from m_reply import envelopes


def decoded(raw):
    """Hn.J(raw, false); escaped frame checksum validation."""
    if len(raw) < 3:
        return None
    frame = raw[1:] if raw[0] == 0 and len(raw) > 3 else raw
    if frame[-1] != 0xbb:
        return None
    out = bytearray()
    i = 1 if frame[0] == 0xbb else 0
    while i < len(frame) - 1:
        b = frame[i]
        if b == 0xbd and i + 1 < len(frame) - 1:
            i += 1
            b = frame[i] ^ 32
        out.append(b)
        i += 1
    return bytes(out[:-1]) if len(out) >= 2 and (sum(out[:-1]) + 1) & 255 == out[-1] else None


def qualifies(data):
    """F1 E5000 raw-instruction branch; readable JADX incorrectly inverts raw case."""
    if not data:
        return False
    if data[0] in (49, 50):
        return len(data) >= 3 and data[1:3] == b'\0\0'
    if len(data) >= 4 and data[0] & 136 == 136 and data[1] in (49, 50):
        return data[2:4] == b'\0\0'
    return (len(data) >= 5 and data[0] == 0 and data[1] & 136 == 136
            and data[2] in (49, 50) and data[3:5] == b'\0\0')


def first_match(raw):
    """Preserve Hn.E ordering, including payload-only fallbacks."""
    candidates = [raw] if raw else []
    if len(raw) > 1 and raw[0] == 0:
        candidates.append(raw[1:])
    for protocol, payload in envelopes(raw):
        candidates.append(payload)
        if len(payload) > 1 and payload[0] == 0:
            candidates.append(payload[1:])
        candidates.append(bytes([protocol]) + payload)
    frame = decoded(raw)
    if frame is not None:
        candidates += [frame[1:], frame]
    return next((data for data in candidates if qualifies(data)), None)
