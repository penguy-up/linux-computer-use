"""Direct /dev/uinput absolute pointer device for Wayland/libinput."""

from __future__ import annotations

import os
import time
from typing import Optional

try:
    import evdev
    from evdev import AbsInfo, ecodes
    HAVE_EVDEV = True
except ImportError:
    HAVE_EVDEV = False


class UInputPointer:
    """Virtual absolute pointer device using Linux kernel /dev/uinput."""

    def __init__(self, width: int = 2560, height: int = 1600):
        if not HAVE_EVDEV:
            raise RuntimeError("evdev library is not installed or available")

        if not os.access("/dev/uinput", os.W_OK):
            raise PermissionError(
                "/dev/uinput is not writable by current user. "
                "Run `scripts/setup_permissions.sh` or run `sudo chmod 666 /dev/uinput` to enable."
            )

        self.width = max(1, width)
        self.height = max(1, height)
        self.current_x = self.width // 2
        self.current_y = self.height // 2

        # Capabilities: ABS_X, ABS_Y, buttons, wheel
        abs_x = AbsInfo(value=self.current_x, min=0, max=self.width, fuzz=0, flat=0, resolution=1)
        abs_y = AbsInfo(value=self.current_y, min=0, max=self.height, fuzz=0, flat=0, resolution=1)

        cap = {
            ecodes.EV_KEY: [
                ecodes.BTN_LEFT,
                ecodes.BTN_RIGHT,
                ecodes.BTN_MIDDLE,
                ecodes.BTN_SIDE,
                ecodes.BTN_EXTRA,
                ecodes.BTN_TOUCH,
            ],
            ecodes.EV_ABS: [
                (ecodes.ABS_X, abs_x),
                (ecodes.ABS_Y, abs_y),
            ],
            ecodes.EV_REL: [
                ecodes.REL_WHEEL,
                ecodes.REL_HWHEEL,
            ],
        }

        self.device = evdev.UInput(
            cap,
            name="Deepin-Computer-Use-Pointer",
            vendor=0x1234,
            product=0x5678,
            version=1,
            input_props=[ecodes.INPUT_PROP_POINTER],
        )
        # Give libinput time to enumerate the new device
        time.sleep(0.3)

    def move_to(self, x: int, y: int):
        """Move cursor to absolute coordinates."""
        clamped_x = max(0, min(self.width, x))
        clamped_y = max(0, min(self.height, y))
        self.current_x = clamped_x
        self.current_y = clamped_y

        self.device.write(ecodes.EV_ABS, ecodes.ABS_X, clamped_x)
        self.device.write(ecodes.EV_ABS, ecodes.ABS_Y, clamped_y)
        self.device.syn()

    def button_down(self, button: str = "left"):
        """Press down a mouse button ('left', 'right', 'middle')."""
        btn_code = self._resolve_button(button)
        self.device.write(ecodes.EV_KEY, btn_code, 1)
        if btn_code == ecodes.BTN_LEFT:
            self.device.write(ecodes.EV_KEY, ecodes.BTN_TOUCH, 1)
        self.device.syn()

    def button_up(self, button: str = "left"):
        """Release a mouse button."""
        btn_code = self._resolve_button(button)
        self.device.write(ecodes.EV_KEY, btn_code, 0)
        if btn_code == ecodes.BTN_LEFT:
            self.device.write(ecodes.EV_KEY, ecodes.BTN_TOUCH, 0)
        self.device.syn()

    def click(self, button: str = "left", count: int = 1, interval_ms: int = 50):
        """Click a mouse button count times."""
        for _ in range(count):
            self.button_down(button)
            time.sleep(interval_ms / 1000.0)
            self.button_up(button)
            if count > 1:
                time.sleep(interval_ms / 1000.0)

    def scroll(self, steps: int = 1, horizontal: bool = False):
        """Scroll vertical or horizontal wheel."""
        axis = ecodes.REL_HWHEEL if horizontal else ecodes.REL_WHEEL
        self.device.write(ecodes.EV_REL, axis, steps)
        self.device.syn()

    def close(self):
        """Close virtual device."""
        if hasattr(self, "device") and self.device:
            self.device.close()

    def _resolve_button(self, button: str) -> int:
        b = button.lower()
        if b in ("left", "btn_left", "1"):
            return ecodes.BTN_LEFT
        if b in ("right", "btn_right", "3"):
            return ecodes.BTN_RIGHT
        if b in ("middle", "btn_middle", "2"):
            return ecodes.BTN_MIDDLE
        return ecodes.BTN_LEFT
