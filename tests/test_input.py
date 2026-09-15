"""Test input event parsing and pointer logic."""

from __future__ import annotations

import pytest
from deepin_computer_use.input.keyboard import normalize_key, parse_key_combo
from deepin_computer_use.input.pointer import get_cursor_position, mouse_move


def test_normalize_key():
    assert normalize_key("enter") == "Return"
    assert normalize_key("esc") == "Escape"
    assert normalize_key("pageup") == "Prior"
    assert normalize_key("f5") == "F5"
    assert normalize_key("a") == "a"


def test_parse_key_combo():
    mods, key = parse_key_combo("Ctrl+C")
    assert mods == ["ctrl"]
    assert key == "C"

    mods, key = parse_key_combo("Ctrl+Alt+Delete")
    assert mods == ["ctrl", "alt"]
    assert key == "Delete"

    mods, key = parse_key_combo("Super")
    assert key == "logo"


def test_pointer_movement_coordinate_tracking():
    mouse_move(450, 650)
    pos = get_cursor_position()
    assert isinstance(pos, tuple)
    assert len(pos) == 2


def test_button_tracking_and_release_all():
    from deepin_computer_use.input.pointer import get_held_buttons, mouse_down, mouse_up, release_all_buttons
    release_all_buttons()
    assert len(get_held_buttons()) == 0
    mouse_down("left")
    assert "left" in get_held_buttons()
    mouse_up("left")
    assert "left" not in get_held_buttons()
    mouse_down("right")
    assert "right" in get_held_buttons()
    released = release_all_buttons()
    assert "right" in released
    assert len(get_held_buttons()) == 0


def test_is_non_ascii_or_complex():
    from deepin_computer_use.input.keyboard import is_non_ascii_or_complex
    assert not is_non_ascii_or_complex("abc123")
    assert is_non_ascii_or_complex("中文输入")
    assert is_non_ascii_or_complex("line1\nline2")
