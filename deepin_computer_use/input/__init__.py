"""Input emulation package."""
from .keyboard import press_key, type_text
from .pointer import (
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
    "press_key",
    "type_text",
    "mouse_move",
    "mouse_click",
    "mouse_down",
    "mouse_up",
    "mouse_drag",
    "mouse_scroll",
    "get_cursor_position",
    "get_held_buttons",
    "release_all_buttons",
]
