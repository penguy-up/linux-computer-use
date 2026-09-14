"""Test Treeland window management integration."""

from __future__ import annotations

from deepin_computer_use.windowing import list_windows


def test_list_windows():
    windows = list_windows()
    assert isinstance(windows, list)
    # On a running Deepin desktop, there should be active windows (dde-shell, control-center, etc.)
    assert len(windows) > 0
    first = windows[0]
    assert "app_id" in first
    assert "title" in first
    assert "backend" in first
