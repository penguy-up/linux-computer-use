"""Test screenshot capturing and payload processing."""

from __future__ import annotations

import base64
import io
from PIL import Image
from deepin_computer_use.screenshot import capture_screenshot, get_screen_size


def test_get_screen_size():
    w, h = get_screen_size()
    assert w > 0
    assert h > 0


def test_get_screen_size_caching():
    w1, h1 = get_screen_size()
    w2, h2 = get_screen_size()
    assert (w1, h1) == (w2, h2)
    # Test force refresh
    w3, h3 = get_screen_size(force_refresh=True)
    assert (w3, h3) == (w1, h1)


def test_capture_screenshot_dimensions_and_rescaling():
    res = capture_screenshot(max_width=800, max_height=600, output_format="png")
    assert res["width"] <= 800
    assert res["height"] <= 600
    assert res["coordinate_width"] >= res["width"]
    assert res["format"] == "png"
    assert res["mime_type"] == "image/png"
    assert res["bytes"] > 0

    # Validate valid decodable image
    raw = base64.b64decode(res["base64_data"])
    with Image.open(io.BytesIO(raw)) as img:
        assert img.size == (res["width"], res["height"])


def test_capture_screenshot_jpeg_compression():
    res = capture_screenshot(max_width=640, max_height=480, output_format="jpeg", quality=60)
    assert res["format"] == "jpeg"
    assert res["mime_type"] == "image/jpeg"
    assert res["quality"] <= 60


def test_capture_screenshot_cropping():
    crop = {"x": 50, "y": 50, "width": 200, "height": 150}
    res = capture_screenshot(crop_rect=crop, output_format="png")
    assert res["width"] > 0
    assert res["height"] > 0
