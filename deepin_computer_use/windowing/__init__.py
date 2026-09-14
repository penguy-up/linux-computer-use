"""Windowing and toplevel management for Deepin OS V25 (Treeland)."""

from .treeland import (
    close_window,
    focus_window,
    list_windows,
    maximize_window,
    minimize_window,
)

__all__ = [
    "list_windows",
    "focus_window",
    "close_window",
    "maximize_window",
    "minimize_window",
]
