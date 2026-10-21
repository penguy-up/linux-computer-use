"""Treeland window management for Deepin."""

from .treeland import (
    FocusGuard,
    close_window,
    focus_window,
    list_windows,
    maximize_window,
    minimize_window,
)

__all__ = [
    "FocusGuard",
    "list_windows",
    "focus_window",
    "close_window",
    "maximize_window",
    "minimize_window",
]
