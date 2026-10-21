"""Input injection subsystem for Deepin OS V25 (Treeland Wayland)."""

from .keyboard import normalize_key, parse_key_combo, press_key, type_text
from .pointer import (
    CursorGuard,
    get_cursor_position,
    get_held_buttons,
    mouse_click,
    mouse_down,
    mouse_drag,
    mouse_move,
    mouse_scroll,
    mouse_up,
    release_all_buttons,
)

__all__ = [
    "CursorGuard",
    "mouse_move",
    "mouse_down",
    "mouse_up",
    "mouse_click",
    "mouse_drag",
    "mouse_scroll",
    "get_cursor_position",
    "get_held_buttons",
    "release_all_buttons",
    "press_key",
    "type_text",
    "normalize_key",
    "parse_key_combo",
]
