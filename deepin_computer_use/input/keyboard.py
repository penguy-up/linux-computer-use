"""Keyboard event injection for Deepin OS V25 (Treeland Wayland)."""

from __future__ import annotations

import os
import subprocess
import time
from typing import List

from ..config import (
    WAYLAND_DISPLAY,
    WL_COPY_BIN,
    WLRCTL_BIN,
    WTYPE_BIN,
    XDOTOOL_BIN,
    XDG_RUNTIME_DIR,
)

# Canonical modifier normalization
MODIFIERS_MAP = {
    "ctrl": "ctrl",
    "control": "ctrl",
    "alt": "alt",
    "option": "alt",
    "shift": "shift",
    "super": "logo",
    "meta": "logo",
    "win": "logo",
    "cmd": "logo",
    "command": "logo",
    "logo": "logo",
}

# Special key normalization to XKB keysym names accepted by wtype / xkbcommon
SPECIAL_KEYS_MAP = {
    "enter": "Return",
    "return": "Return",
    "escape": "Escape",
    "esc": "Escape",
    "tab": "Tab",
    "backspace": "BackSpace",
    "delete": "Delete",
    "del": "Delete",
    "space": "space",
    "home": "Home",
    "end": "End",
    "pageup": "Prior",
    "page_up": "Prior",
    "pagedown": "Next",
    "page_down": "Next",
    "prior": "Prior",
    "next": "Next",
    "arrowleft": "Left",
    "left": "Left",
    "arrowright": "Right",
    "right": "Right",
    "arrowup": "Up",
    "up": "Up",
    "arrowdown": "Down",
    "down": "Down",
    "capslock": "Caps_Lock",
    "insert": "Insert",
    "printscreen": "Print",
    "print": "Print",
}


def normalize_key(key: str) -> str:
    """Normalize user-supplied key name to XKB keysym name."""
    k = key.strip()
    low = k.lower()
    if low in SPECIAL_KEYS_MAP:
        return SPECIAL_KEYS_MAP[low]
    if low.startswith("f") and len(low) in (2, 3) and low[1:].isdigit():
        return f"F{low[1:]}"
    # Single alphanumeric character
    if len(k) == 1:
        return k
    return k


def parse_key_combo(combo_str: str) -> tuple[List[str], str]:
    """Parse a combo like 'Ctrl+Shift+T' into ([modifiers], key)."""
    parts = [p.strip() for p in combo_str.split("+") if p.strip()]
    if not parts:
        raise ValueError("Empty key combination")

    modifiers: List[str] = []
    key = ""

    if len(parts) == 1:
        part = parts[0]
        low = part.lower()
        if low in MODIFIERS_MAP:
            return [], MODIFIERS_MAP[low]
        return [], normalize_key(part)

    for i, part in enumerate(parts):
        low = part.lower()
        if low in MODIFIERS_MAP and i < len(parts) - 1:
            mod_name = MODIFIERS_MAP[low]
            if mod_name not in modifiers:
                modifiers.append(mod_name)
        else:
            key = normalize_key(part)

    if not key and modifiers:
        # User might just want to press a modifier, e.g. "Super"
        key = modifiers.pop()

    return modifiers, key


# Flag to absorb the first-event loss seen on fresh wlroots seats
_keyboard_warmed_up: bool = False


def _warmup_virtual_keyboard() -> None:
    """Send a harmless Shift tap to absorb first-event loss on wlroots seats."""
    global _keyboard_warmed_up
    if _keyboard_warmed_up:
        return

    wtype = WTYPE_BIN or "wtype"
    if wtype:
        env = dict(os.environ)
        env["WAYLAND_DISPLAY"] = WAYLAND_DISPLAY
        env["XDG_RUNTIME_DIR"] = XDG_RUNTIME_DIR
        try:
            subprocess.run([wtype, "-M", "shift", "-m", "shift"], env=env, capture_output=True, timeout=1)
            _keyboard_warmed_up = True
        except Exception:
            pass


def copy_to_clipboard(text: str) -> bool:
    """Copy text to Wayland clipboard using wl-copy (or xclip fallback)."""
    env = dict(os.environ)
    env["WAYLAND_DISPLAY"] = WAYLAND_DISPLAY
    env["XDG_RUNTIME_DIR"] = XDG_RUNTIME_DIR

    wl_copy = WL_COPY_BIN or "wl-copy"
    try:
        res = subprocess.run([wl_copy], input=text.encode("utf-8"), env=env, capture_output=True, timeout=2)
        if res.returncode == 0:
            return True
    except Exception:
        pass

    try:
        res = subprocess.run(["xclip", "-selection", "clipboard"], input=text.encode("utf-8"), env=env, capture_output=True, timeout=2)
        if res.returncode == 0:
            return True
    except Exception:
        pass

    return False


def is_non_ascii_or_complex(text: str) -> bool:
    """Check whether text contains non-ASCII characters (e.g. Chinese, emojis) or newlines."""
    return any(ord(c) >= 128 or c in "\n\r\t" for c in text)


def type_text(
    text: str,
    delay_ms: int = 10,
    method: str = "auto",
) -> bool:
    """Type literal text using Wayland virtual keyboard (wtype/wlrctl) or clipboard paste.
    
    Args:
        text: The string to type.
        delay_ms: Delay in ms between keystrokes when using keyboard typing emulation.
        method: "auto" (default), "type" (keystroke emulation only), or "clipboard" (paste via Ctrl+V).
                "auto" automatically switches to clipboard paste if text contains Chinese/Unicode,
                newlines, or is longer than 15 characters, ensuring zero lost characters.
    """
    if not text:
        return True

    env = dict(os.environ)
    env["WAYLAND_DISPLAY"] = WAYLAND_DISPLAY
    env["XDG_RUNTIME_DIR"] = XDG_RUNTIME_DIR

    use_clipboard = False
    if method == "clipboard":
        use_clipboard = True
    elif method == "auto":
        # Fast path for Chinese, complex unicode, or longer texts
        if is_non_ascii_or_complex(text) or len(text) > 15:
            use_clipboard = True

    if use_clipboard:
        if copy_to_clipboard(text):
            time.sleep(0.02)
            try:
                press_key("Ctrl+V")
                return True
            except Exception:
                pass
        if method == "clipboard":
            raise RuntimeError("Failed to inject text via clipboard paste")

    _warmup_virtual_keyboard()

    # 1. Prefer wtype
    wtype = WTYPE_BIN or "wtype"
    if wtype:
        try:
            cmd = [wtype]
            if delay_ms > 0:
                cmd.extend(["-s", str(delay_ms)])
            cmd.extend(["--", text])
            res = subprocess.run(cmd, env=env, capture_output=True, timeout=10)
            if res.returncode == 0:
                return True
        except Exception:
            pass

    # 2. Fallback: wlrctl keyboard type
    wlrctl = WLRCTL_BIN or "wlrctl"
    if wlrctl:
        try:
            cmd = [wlrctl, "keyboard", "type", text]
            res = subprocess.run(cmd, env=env, capture_output=True, timeout=10)
            if res.returncode == 0:
                return True
        except Exception:
            pass

    # 3. Fallback: xdotool type (for XWayland active windows)
    xdotool = XDOTOOL_BIN or "xdotool"
    if xdotool:
        try:
            cmd = [xdotool, "type", "--delay", str(delay_ms), text]
            res = subprocess.run(cmd, env=env, capture_output=True, timeout=10)
            if res.returncode == 0:
                return True
        except Exception:
            pass

    raise RuntimeError("Failed to type text: no working Wayland virtual keyboard or clipboard found")


def press_key(key_combo: str) -> bool:
    """Press a key or key combination (e.g. 'Ctrl+C', 'Super', 'Return')."""
    _warmup_virtual_keyboard()
    modifiers, key = parse_key_combo(key_combo)

    env = dict(os.environ)
    env["WAYLAND_DISPLAY"] = WAYLAND_DISPLAY
    env["XDG_RUNTIME_DIR"] = XDG_RUNTIME_DIR

    # 1. Prefer wtype with modifier flags
    wtype = WTYPE_BIN or "wtype"
    if wtype:
        cmd = [wtype]
        for m in modifiers:
            cmd.extend(["-M", m])
        if key:
            cmd.extend(["-k", key])
        for m in reversed(modifiers):
            cmd.extend(["-m", m])

        try:
            res = subprocess.run(cmd, env=env, capture_output=True, timeout=5)
            if res.returncode == 0:
                return True
        except Exception:
            pass

    # 2. Fallback: xdotool key
    xdotool = XDOTOOL_BIN or "xdotool"
    if xdotool:
        try:
            # Map back to xdotool syntax
            x_mods = []
            for m in modifiers:
                if m == "logo":
                    x_mods.append("Super")
                elif m == "ctrl":
                    x_mods.append("ctrl")
                elif m == "alt":
                    x_mods.append("alt")
                elif m == "shift":
                    x_mods.append("shift")
            chord = "+".join(x_mods + [key]) if x_mods else key
            res = subprocess.run([xdotool, "key", chord], env=env, capture_output=True, timeout=5)
            if res.returncode == 0:
                return True
        except Exception:
            pass

    raise RuntimeError(f"Failed to press key combination: {key_combo}")
