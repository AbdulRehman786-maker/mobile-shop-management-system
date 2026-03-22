"""
Lightweight image signature detection (no external deps).
"""
from __future__ import annotations


def detect_image_type(header: bytes) -> str | None:
    """
    Detect common image types from header bytes.
    Returns: 'jpeg' | 'png' | 'gif' | 'webp' or None.
    """
    if not header:
        return None

    # JPEG: FF D8 FF
    if header[:3] == b"\xFF\xD8\xFF":
        return "jpeg"

    # PNG: 89 50 4E 47 0D 0A 1A 0A
    if header[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"

    # GIF: GIF87a / GIF89a
    if header[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"

    # WEBP: RIFF....WEBP
    if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return "webp"

    return None
