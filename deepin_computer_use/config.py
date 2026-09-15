"""Configuration and environment detection for Deepin Computer Use."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

# Base directories
PACKAGE_ROOT = Path(__file__).parent.resolve()
PROJECT_ROOT = PACKAGE_ROOT.parent.resolve()
BUNDLED_BIN_DIR = PROJECT_ROOT / "bin"
VENDOR_DIR = PACKAGE_ROOT / "vendor"

# Add vendor directory to sys.path if present
import sys
if VENDOR_DIR.exists() and str(VENDOR_DIR) not in sys.path:
    sys.path.insert(0, str(VENDOR_DIR))


def find_executable(name: str) -> str | None:
    """Find executable by looking in bundled bin first, then system PATH."""
    # 1. Check bundled bin dir
    bundled_path = BUNDLED_BIN_DIR / name
    if bundled_path.is_file() and os.access(bundled_path, os.X_OK):
        return str(bundled_path)

    # 2. Check system PATH
    system_path = shutil.which(name)
    if system_path:
        return system_path

    # 3. Check common user / system directories
    user_local_bin = str(Path.home() / ".local" / "bin" / name)
    for fallback in [f"/usr/bin/{name}", f"/usr/local/bin/{name}", user_local_bin]:
        if os.path.isfile(fallback) and os.access(fallback, os.X_OK):
            return fallback

    return None


# Environment variables
WAYLAND_DISPLAY = os.environ.get("WAYLAND_DISPLAY", "treeland.socket")
XDG_RUNTIME_DIR = os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
DISPLAY = os.environ.get("DISPLAY", ":1")

# Binaries
GRIM_BIN = find_executable("grim")
WLRCTL_BIN = find_executable("wlrctl")
WTYPE_BIN = find_executable("wtype")
WL_COPY_BIN = find_executable("wl-copy")
XDOTOOL_BIN = find_executable("xdotool")

# Default image / screenshot constraints
DEFAULT_MAX_WIDTH = 1920
DEFAULT_MAX_HEIGHT = 1080
DEFAULT_JPEG_QUALITY = 80
DEFAULT_SCREENSHOT_FORMAT = "png"
MAX_PAYLOAD_BYTES = 4 * 1024 * 1024  # 4 MB
