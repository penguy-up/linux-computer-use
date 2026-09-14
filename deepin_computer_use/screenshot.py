"""Screenshot capture engine for Deepin OS V25 (Treeland Wayland)."""

from __future__ import annotations

import base64
import io
import os
import subprocess
import tempfile
import time
from typing import Any, Dict, Optional, Tuple

from PIL import Image

from .config import (
    DEFAULT_JPEG_QUALITY,
    DEFAULT_MAX_HEIGHT,
    DEFAULT_MAX_WIDTH,
    DEFAULT_SCREENSHOT_FORMAT,
    GRIM_BIN,
    MAX_PAYLOAD_BYTES,
    WAYLAND_DISPLAY,
    XDG_RUNTIME_DIR,
)


def get_screen_size() -> Tuple[int, int]:
    """Get logical or physical desktop dimensions using grim capture or probe."""
    try:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
            temp_path = tf.name
        cmd = [GRIM_BIN or "grim", temp_path]
        env = dict(os.environ)
        env["WAYLAND_DISPLAY"] = WAYLAND_DISPLAY
        env["XDG_RUNTIME_DIR"] = XDG_RUNTIME_DIR
        subprocess.run(cmd, env=env, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        with Image.open(temp_path) as img:
            w, h = img.size
        os.unlink(temp_path)
        return w, h
    except Exception:
        # Fallback to standard 1080p
        return 1920, 1080


def capture_screenshot_raw(
    geometry: Optional[str] = None,
    include_cursor: bool = False,
    output_format: str = "png",
    quality: int = DEFAULT_JPEG_QUALITY,
) -> Tuple[bytes, str, int, int]:
    """Capture raw screenshot bytes using grim (or DDE fallback).
    
    Returns: (image_bytes, mime_type, original_width, original_height)
    """
    env = dict(os.environ)
    env["WAYLAND_DISPLAY"] = WAYLAND_DISPLAY
    env["XDG_RUNTIME_DIR"] = XDG_RUNTIME_DIR

    grim = GRIM_BIN or "grim"
    suffix = ".jpg" if output_format.lower() in ("jpeg", "jpg") else ".png"
    mime_type = "image/jpeg" if suffix == ".jpg" else "image/png"

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tf:
        temp_path = tf.name

    try:
        # 1. Try grim first (fastest Wayland zwlr_screencopy_manager_v1)
        cmd = [grim]
        if include_cursor:
            cmd.append("-c")
        if geometry:
            cmd.extend(["-g", geometry])
        if suffix == ".jpg":
            cmd.extend(["-t", "jpeg", "-q", str(quality)])
        else:
            cmd.extend(["-t", "png"])
        cmd.append(temp_path)

        res = subprocess.run(cmd, env=env, capture_output=True, timeout=5)
        if res.returncode == 0 and os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
            with Image.open(temp_path) as img:
                w, h = img.size
            with open(temp_path, "rb") as f:
                data = f.read()
            return data, mime_type, w, h
    except Exception:
        pass

    # 2. Fallback: Deepin Screen Recorder CLI
    try:
        dsr_cmd = ["deepin-screen-recorder", "-f", "-s", temp_path, "-n"]
        subprocess.run(dsr_cmd, env=env, capture_output=True, timeout=8)
        if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
            with Image.open(temp_path) as img:
                w, h = img.size
            with open(temp_path, "rb") as f:
                data = f.read()
            return data, mime_type, w, h
    except Exception:
        pass
    finally:
        if os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except OSError:
                pass

    raise RuntimeError("Failed to capture screenshot using grim and deepin-screen-recorder")


def capture_screenshot(
    max_width: Optional[int] = DEFAULT_MAX_WIDTH,
    max_height: Optional[int] = DEFAULT_MAX_HEIGHT,
    scale: Optional[float] = None,
    output_format: str = DEFAULT_SCREENSHOT_FORMAT,
    quality: int = DEFAULT_JPEG_QUALITY,
    crop_rect: Optional[Dict[str, int]] = None,
    include_cursor: bool = False,
    max_bytes: int = MAX_PAYLOAD_BYTES,
) -> Dict[str, Any]:
    """Capture, process, downscale/compress, and encode screenshot as MCP payload.
    
    crop_rect format: {"x": int, "y": int, "width": int, "height": int}
    """
    geometry = None
    if crop_rect:
        cx = crop_rect.get("x", 0)
        cy = crop_rect.get("y", 0)
        cw = crop_rect.get("width", 100)
        ch = crop_rect.get("height", 100)
        geometry = f"{cx},{cy} {cw}x{ch}"

    raw_bytes, mime, orig_w, orig_h = capture_screenshot_raw(
        geometry=geometry,
        include_cursor=include_cursor,
        output_format="png",  # capture lossless first for processing
        quality=quality,
    )

    # Process using Pillow
    img = Image.open(io.BytesIO(raw_bytes))
    coord_w, coord_h = img.size

    # Calculate target dimensions
    target_w = coord_w
    target_h = coord_h

    if scale is not None and scale > 0:
        target_w = max(1, int(round(coord_w * scale)))
        target_h = max(1, int(round(coord_h * scale)))

    if max_width is not None and target_w > max_width:
        ratio = max_width / float(target_w)
        target_w = max_width
        target_h = max(1, int(round(target_h * ratio)))

    if max_height is not None and target_h > max_height:
        ratio = max_height / float(target_h)
        target_h = max_height
        target_w = max(1, int(round(target_w * ratio)))

    is_resized = (target_w != coord_w) or (target_h != coord_h)
    if is_resized:
        img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)

    # Determine encoding format
    fmt = output_format.lower()
    if fmt in ("jpg", "jpeg"):
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        target_mime = "image/jpeg"
        save_format = "JPEG"
    else:
        target_mime = "image/png"
        save_format = "PNG"

    # Encode with byte-size bound enforcement
    current_quality = quality
    buf = io.BytesIO()
    if save_format == "JPEG":
        img.save(buf, format="JPEG", quality=current_quality, optimize=True)
    else:
        img.save(buf, format="PNG", optimize=True)

    # If payload too large and format is JPEG, reduce quality
    while buf.tell() > max_bytes and save_format == "JPEG" and current_quality > 30:
        current_quality -= 10
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=current_quality, optimize=True)

    # If PNG is still too large, fallback to compressed JPEG
    if buf.tell() > max_bytes and save_format == "PNG":
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        buf = io.BytesIO()
        save_format = "JPEG"
        target_mime = "image/jpeg"
        current_quality = 70
        img.save(buf, format="JPEG", quality=current_quality, optimize=True)

    final_bytes = buf.getvalue()
    b64_data = base64.b64encode(final_bytes).decode("ascii")
    effective_scale = (target_w / float(coord_w)) if coord_w > 0 else 1.0

    return {
        "mime_type": target_mime,
        "data_url": f"data:{target_mime};base64,{b64_data}",
        "base64_data": b64_data,
        "width": target_w,
        "height": target_h,
        "coordinate_width": coord_w,
        "coordinate_height": coord_h,
        "scale": round(effective_scale, 4),
        "resized": is_resized,
        "bytes": len(final_bytes),
        "original_bytes": len(raw_bytes),
        "format": save_format.lower(),
        "quality": current_quality if save_format == "JPEG" else None,
        "timestamp": time.time(),
    }
