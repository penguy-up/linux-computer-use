"""Unified mouse pointer controller with UInput and CLI fallback."""

from __future__ import annotations

import os
import subprocess
import time
from typing import Optional, Tuple

from ..config import XDOTOOL_BIN
from .uinput_device import UInputPointer

# Global singleton instance for pointer device
_uinput_pointer: Optional[UInputPointer] = None
_last_cursor_x: int = 500
_last_cursor_y: int = 500
_held_buttons: set[str] = set()


def get_held_buttons() -> set[str]:
    """Return a copy of currently held mouse buttons."""
    return set(_held_buttons)


def release_all_buttons() -> list[str]:
    """Release any mouse buttons currently marked as held down."""
    global _held_buttons
    released = []
    for btn in list(_held_buttons):
        try:
            mouse_up(btn)
            released.append(btn)
        except Exception:
            _held_buttons.discard(btn)
    return released


def get_uinput_pointer(width: int = 2560, height: int = 1600) -> Optional[UInputPointer]:
    """Get or lazily initialize the UInput pointer device."""
    global _uinput_pointer
    if _uinput_pointer is None:
        try:
            _uinput_pointer = UInputPointer(width=width, height=height)
        except Exception:
            _uinput_pointer = None
    return _uinput_pointer


def mouse_move(x: int, y: int, screen_width: int = 2560, screen_height: int = 1600) -> bool:
    """Move cursor to (x, y) coordinates."""
    global _last_cursor_x, _last_cursor_y
    _last_cursor_x = x
    _last_cursor_y = y

    # 1. Try uinput absolute pointer
    ptr = get_uinput_pointer(width=screen_width, height=screen_height)
    if ptr:
        try:
            ptr.move_to(x, y)
            return True
        except Exception:
            pass

    # 2. Try ydotool if socket available
    ydotool_sock = os.environ.get("YDOTOOL_SOCKET", "/tmp/.ydotool_socket")
    if os.path.exists(ydotool_sock) or os.path.exists("/run/user/1000/.ydotool_socket"):
        try:
            res = subprocess.run(["ydotool", "mousemove", "--absolute", str(x), str(y)], capture_output=True, timeout=2)
            if res.returncode == 0:
                return True
        except Exception:
            pass

    # 3. Fallback to xdotool
    if XDOTOOL_BIN:
        try:
            res = subprocess.run([XDOTOOL_BIN, "mousemove", str(x), str(y)], capture_output=True, timeout=2)
            if res.returncode == 0:
                return True
        except Exception:
            pass

    raise RuntimeError(f"Failed to move mouse to ({x}, {y}): no working mouse injection backend available")


def mouse_down(button: str = "left") -> bool:
    """Press down a mouse button."""
    global _held_buttons
    ptr = get_uinput_pointer()
    if ptr:
        try:
            ptr.button_down(button)
            _held_buttons.add(button)
            return True
        except Exception:
            pass

    # Fallback to xdotool
    if XDOTOOL_BIN:
        btn_num = "1" if button == "left" else "3" if button == "right" else "2"
        try:
            res = subprocess.run([XDOTOOL_BIN, "mousedown", btn_num], capture_output=True, timeout=2)
            if res.returncode == 0:
                _held_buttons.add(button)
                return True
        except Exception:
            pass

    raise RuntimeError(f"Failed to press mouse button '{button}': no working mouse injection backend available")


def mouse_up(button: str = "left") -> bool:
    """Release a mouse button."""
    global _held_buttons
    ptr = get_uinput_pointer()
    if ptr:
        try:
            ptr.button_up(button)
            _held_buttons.discard(button)
            return True
        except Exception:
            pass

    if XDOTOOL_BIN:
        btn_num = "1" if button == "left" else "3" if button == "right" else "2"
        try:
            res = subprocess.run([XDOTOOL_BIN, "mouseup", btn_num], capture_output=True, timeout=2)
            if res.returncode == 0:
                _held_buttons.discard(button)
                return True
        except Exception:
            pass

    raise RuntimeError(f"Failed to release mouse button '{button}': no working mouse injection backend available")


def mouse_click(
    x: Optional[int] = None,
    y: Optional[int] = None,
    button: str = "left",
    count: int = 1,
) -> bool:
    """Move (optionally) and click the mouse button."""
    if x is not None and y is not None:
        mouse_move(x, y)
        time.sleep(0.05)

    ptr = get_uinput_pointer()
    if ptr:
        try:
            ptr.click(button=button, count=count)
            return True
        except Exception:
            pass

    # Try ydotool click
    ydotool_sock = os.environ.get("YDOTOOL_SOCKET", "/tmp/.ydotool_socket")
    if os.path.exists(ydotool_sock):
        btn_hex = "0x110" if button == "left" else "0x111" if button == "right" else "0x112"
        try:
            res = subprocess.run(["ydotool", "click", "--repeat", str(count), btn_hex], capture_output=True, timeout=2)
            if res.returncode == 0:
                return True
        except Exception:
            pass

    # Fallback to xdotool
    if XDOTOOL_BIN:
        btn_num = "1" if button == "left" else "3" if button == "right" else "2"
        try:
            res = subprocess.run([XDOTOOL_BIN, "click", "--repeat", str(count), btn_num], capture_output=True, timeout=2)
            if res.returncode == 0:
                return True
        except Exception:
            pass

    raise RuntimeError(f"Failed to click mouse button '{button}': no working mouse injection backend available")


def mouse_drag(
    start_x: int,
    start_y: int,
    end_x: int,
    end_y: int,
    button: str = "left",
    steps: int = 10,
    delay_ms: int = 20,
) -> bool:
    """Drag from (start_x, start_y) to (end_x, end_y)."""
    mouse_move(start_x, start_y)
    time.sleep(0.05)
    mouse_down(button)
    time.sleep(0.05)

    for i in range(1, steps + 1):
        cur_x = int(start_x + (end_x - start_x) * (i / float(steps)))
        cur_y = int(start_y + (end_y - start_y) * (i / float(steps)))
        mouse_move(cur_x, cur_y)
        time.sleep(delay_ms / 1000.0)

    time.sleep(0.05)
    mouse_up(button)
    return True


def mouse_scroll(direction: str = "down", amount: int = 2) -> bool:
    """Scroll wheel in given direction ('up', 'down', 'left', 'right')."""
    d = direction.lower()
    steps = amount if d in ("up", "left") else -amount
    horizontal = d in ("left", "right")

    ptr = get_uinput_pointer()
    if ptr:
        try:
            ptr.scroll(steps=steps, horizontal=horizontal)
            return True
        except Exception:
            pass

    # Fallback to xdotool
    if XDOTOOL_BIN:
        btn = "4" if d == "up" else "5" if d == "down" else "6" if d == "left" else "7"
        try:
            res = subprocess.run([XDOTOOL_BIN, "click", "--repeat", str(abs(amount)), btn], capture_output=True, timeout=2)
            if res.returncode == 0:
                return True
        except Exception:
            pass

    raise RuntimeError(f"Failed to scroll mouse {direction}: no working mouse injection backend available")


def get_cursor_position() -> Tuple[int, int]:
    """Return the current cursor coordinate (x, y)."""
    # If xdotool can get it, query xdotool
    if XDOTOOL_BIN:
        try:
            res = subprocess.run([XDOTOOL_BIN, "getmouselocation"], capture_output=True, text=True, timeout=1)
            if res.returncode == 0:
                # format: x:200 y:300 screen:0 window:123
                parts = res.stdout.strip().split()
                x = int(parts[0].split(":")[1])
                y = int(parts[1].split(":")[1])
                return x, y
        except Exception:
            pass
    return _last_cursor_x, _last_cursor_y
