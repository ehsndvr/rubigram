"""Media helpers (OGG/Opus duration without external dependencies)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional


def parse_ogg_opus_duration_ms(path: "str | Path") -> float:
    """Duration of an OGG/Opus file in milliseconds (``0.0`` when it cannot be read)."""
    data = Path(path).read_bytes()
    offset = 0
    pre_skip = 0
    found_opus_head = False
    last_granule_position: Optional[int] = None
    while offset + 27 <= len(data):
        if data[offset : offset + 4] != b"OggS":
            next_offset = data.find(b"OggS", offset + 1)
            if next_offset < 0:
                break
            offset = next_offset
            continue
        page_segments = data[offset + 26]
        header_size = 27 + page_segments
        if offset + header_size > len(data):
            break
        segment_table = data[offset + 27 : offset + header_size]
        payload_size = sum(segment_table)
        page_end = offset + header_size + payload_size
        if page_end > len(data):
            break
        granule_position = int.from_bytes(data[offset + 6 : offset + 14], "little", signed=False)
        if granule_position:
            last_granule_position = granule_position
        payload = data[offset + header_size : page_end]
        payload_offset = 0
        packet = bytearray()
        for segment_length in segment_table:
            packet.extend(payload[payload_offset : payload_offset + segment_length])
            payload_offset += segment_length
            if segment_length < 255:
                if not found_opus_head and packet.startswith(b"OpusHead") and len(packet) >= 12:
                    pre_skip = int.from_bytes(packet[10:12], "little", signed=False)
                    found_opus_head = True
                packet.clear()
        offset = page_end
    if not found_opus_head or last_granule_position is None:
        return 0.0
    return round(max(0, last_granule_position - pre_skip) * 1000.0 / 48000.0, 3)


__all__ = ["parse_ogg_opus_duration_ms"]
