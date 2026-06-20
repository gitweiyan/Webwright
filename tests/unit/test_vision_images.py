from __future__ import annotations

import io
from pathlib import Path

import numpy as np
from PIL import Image

from webwright.utils.vision_images import compress_image_for_vision


def _baseline_jpeg_bytes(image: np.ndarray) -> bytes:
    buffer = io.BytesIO()
    Image.fromarray(image).save(buffer, format="JPEG")
    return buffer.getvalue()


def _sample_screenshot_path() -> Path | None:
    root = Path(__file__).resolve().parents[2] / "outputs" / "m3a"
    if not root.exists():
        return None
    candidates = sorted(root.glob("*/screenshots/step_*_before.png"))
    return candidates[0] if candidates else None


def test_compress_image_for_vision_respects_max_bytes():
    image = np.zeros((2400, 1080, 3), dtype=np.uint8)
    image[100:300, 100:300] = (255, 0, 0)
    jpeg_bytes = compress_image_for_vision(image, max_bytes=100_000, max_long_edge=1280)
    assert jpeg_bytes.startswith(b"\xff\xd8")
    assert len(jpeg_bytes) <= 100_000


def test_compress_image_for_vision_reduces_default_jpeg_size():
    sample = _sample_screenshot_path()
    if sample is None:
        return
    image = np.array(Image.open(sample))
    baseline = _baseline_jpeg_bytes(image)
    compressed = compress_image_for_vision(image, max_bytes=100_000, max_long_edge=1280)
    assert len(compressed) <= 100_000
    assert len(compressed) < len(baseline)


def test_compress_image_for_vision_downscales_long_edge():
    image = Image.new("RGB", (1080, 2400), color=(120, 120, 120))
    jpeg_bytes = compress_image_for_vision(image, max_bytes=100_000, max_long_edge=1280)
    decoded = Image.open(io.BytesIO(jpeg_bytes))
    assert max(decoded.size) <= 1280
