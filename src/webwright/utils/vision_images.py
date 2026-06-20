from __future__ import annotations

import io
from math import sqrt

import numpy as np
from PIL import Image


def compress_image_for_vision(
    image: np.ndarray | Image.Image,
    *,
    max_bytes: int = 100_000,
    max_long_edge: int | None = 1280,
    min_quality: int = 45,
) -> bytes:
    """Return JPEG bytes sized for vision-model calls.

    Applies optional long-edge downscale, then reduces JPEG quality and size
    until the payload is at most ``max_bytes``.
    """
    if max_bytes <= 0:
        raise ValueError("max_bytes must be positive")

    pil_image = image if isinstance(image, Image.Image) else Image.fromarray(image)
    if pil_image.mode not in ("RGB", "L"):
        pil_image = pil_image.convert("RGB")

    working = _maybe_downscale_long_edge(pil_image, max_long_edge)
    jpeg_bytes = _encode_jpeg(working, quality=85)
    if len(jpeg_bytes) <= max_bytes:
        return jpeg_bytes

    quality = 85
    while quality >= min_quality:
        jpeg_bytes = _encode_jpeg(working, quality=quality)
        if len(jpeg_bytes) <= max_bytes:
            return jpeg_bytes
        quality -= 10

    scale = min(1.0, sqrt(max_bytes / max(len(jpeg_bytes), 1)) * 0.9)
    for _ in range(4):
        new_width = max(1, int(working.width * scale))
        new_height = max(1, int(working.height * scale))
        if (new_width, new_height) == working.size:
            break
        working = working.resize((new_width, new_height), Image.LANCZOS)
        jpeg_bytes = _encode_jpeg(working, quality=max(min_quality, 75))
        if len(jpeg_bytes) <= max_bytes:
            return jpeg_bytes
        scale *= 0.8

    return jpeg_bytes


def _maybe_downscale_long_edge(image: Image.Image, max_long_edge: int | None) -> Image.Image:
    if max_long_edge is None or max_long_edge <= 0:
        return image
    long_edge = max(image.width, image.height)
    if long_edge <= max_long_edge:
        return image
    scale = max_long_edge / long_edge
    new_width = max(1, int(image.width * scale))
    new_height = max(1, int(image.height * scale))
    return image.resize((new_width, new_height), Image.LANCZOS)


def _encode_jpeg(image: Image.Image, *, quality: int) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=quality, optimize=True)
    return buffer.getvalue()
