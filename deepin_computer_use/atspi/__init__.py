"""AT-SPI accessibility tree inspection and actions for Deepin."""

from .tree import (
    get_accessibility_tree,
    get_active_window,
    list_accessible_apps,
    perform_accessibility_action,
    set_element_value,
)

__all__ = [
    "list_accessible_apps",
    "get_active_window",
    "get_accessibility_tree",
    "perform_accessibility_action",
    "set_element_value",
]
