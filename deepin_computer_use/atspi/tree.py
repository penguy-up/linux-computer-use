"""AT-SPI2 accessibility integration for Deepin Linux desktop."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

try:
    import gi
    gi.require_version("Atspi", "2.0")
    from gi.repository import Atspi
    HAVE_ATSPI = True
except Exception:
    HAVE_ATSPI = False


def list_accessible_apps() -> List[Dict[str, Any]]:
    """List accessible applications on current desktop."""
    if not HAVE_ATSPI:
        return []

    apps: List[Dict[str, Any]] = []
    try:
        desktop = Atspi.get_desktop(0)
        for i in range(desktop.get_child_count()):
            app = desktop.get_child_at_index(i)
            if app:
                name = app.get_name() or "Unnamed"
                apps.append({
                    "index": i,
                    "name": name,
                    "role": app.get_role_name(),
                    "windows_count": app.get_child_count(),
                })
    except Exception:
        pass
    return apps


def get_active_window() -> Tuple[Optional[str], Optional[str]]:
    """Return the name of the currently active/focused application and window title.
    
    Returns:
        (app_name, window_title) or (None, None) if undetectable.
    """
    if not HAVE_ATSPI:
        return None, None

    try:
        desktop = Atspi.get_desktop(0)
        for i in range(desktop.get_child_count()):
            app = desktop.get_child_at_index(i)
            if not app:
                continue
            app_name = app.get_name() or ""
            for j in range(app.get_child_count()):
                win = app.get_child_at_index(j)
                if not win:
                    continue
                try:
                    state_set = win.get_state_set()
                    if state_set and (
                        state_set.contains(Atspi.StateType.ACTIVE)
                        or state_set.contains(Atspi.StateType.FOCUSED)
                    ):
                        return app_name, win.get_name() or ""
                except Exception:
                    continue
    except Exception:
        pass
    return None, None


def _node_to_dict(
    accessible: Any,
    current_depth: int,
    max_depth: int,
    node_counter: List[int],
    max_nodes: int,
) -> Optional[Dict[str, Any]]:
    """Recursively convert AtspiAccessible into clean JSON-serializable dict."""
    if node_counter[0] >= max_nodes:
        return None

    node_counter[0] += 1
    node_id = node_counter[0]

    name = accessible.get_name() or ""
    role = accessible.get_role_name() or ""
    desc = accessible.get_description() or ""

    # Get bounding coordinates
    bounds = None
    try:
        comp = accessible.get_component_iface()
        if comp:
            rect = comp.get_extents(Atspi.CoordType.SCREEN)
            bounds = {
                "x": rect.x,
                "y": rect.y,
                "width": rect.width,
                "height": rect.height,
            }
    except Exception:
        pass

    # Get available actions
    actions: List[str] = []
    try:
        act = accessible.get_action_iface()
        if act:
            for a_idx in range(act.get_n_actions()):
                act_name = act.get_action_name(a_idx)
                if act_name:
                    actions.append(act_name)
    except Exception:
        pass

    # States
    states: List[str] = []
    try:
        state_set = accessible.get_state_set()
        if state_set:
            # Common useful states
            for s in ("focused", "visible", "showing", "enabled", "focusable", "checked", "selectable", "active"):
                state_enum = getattr(Atspi.StateType, s.upper(), None)
                if state_enum is not None and state_set.contains(state_enum):
                    states.append(s)
    except Exception:
        pass

    children: List[Dict[str, Any]] = []
    if current_depth < max_depth and node_counter[0] < max_nodes:
        child_count = accessible.get_child_count()
        for i in range(child_count):
            child = accessible.get_child_at_index(i)
            if child:
                child_dict = _node_to_dict(child, current_depth + 1, max_depth, node_counter, max_nodes)
                if child_dict:
                    children.append(child_dict)

    return {
        "id": node_id,
        "name": name,
        "role": role,
        "description": desc,
        "bounds": bounds,
        "actions": actions,
        "states": states,
        "children": children,
    }


def get_accessibility_tree(
    app_name: Optional[str] = None,
    max_depth: int = 4,
    max_nodes: int = 150,
) -> Dict[str, Any]:
    """Extract accessibility tree for target application or whole desktop."""
    if not HAVE_ATSPI:
        return {"error": "AT-SPI 2.0 is not available in Python environment"}

    desktop = Atspi.get_desktop(0)
    counter = [0]

    if app_name:
        target_app = None
        for i in range(desktop.get_child_count()):
            app = desktop.get_child_at_index(i)
            if app and app_name.lower() in (app.get_name() or "").lower():
                target_app = app
                break

        if not target_app:
            return {"error": f"Application '{app_name}' not found in accessibility bus"}

        tree = _node_to_dict(target_app, 0, max_depth, counter, max_nodes)
        return {
            "app": target_app.get_name(),
            "nodes_extracted": counter[0],
            "tree": tree,
        }

    # Full desktop tree
    app_trees = []
    for i in range(desktop.get_child_count()):
        if counter[0] >= max_nodes:
            break
        app = desktop.get_child_at_index(i)
        if app:
            app_tree = _node_to_dict(app, 0, max_depth, counter, max_nodes)
            if app_tree:
                app_trees.append(app_tree)

    return {
        "desktop": desktop.get_name(),
        "nodes_extracted": counter[0],
        "apps": app_trees,
    }


def _find_node_by_selector(accessible: Any, selector: str | int, counter: Optional[List[int]] = None) -> Optional[Any]:
    """Locate an AtspiAccessible by node ID, element name, role, or description."""
    if counter is None:
        counter = [0]
    counter[0] += 1
    current_id = counter[0]

    # 1. Match by numeric node ID
    target_id: Optional[int] = None
    if isinstance(selector, int):
        target_id = selector
    elif isinstance(selector, str) and selector.isdigit():
        target_id = int(selector)

    if target_id is not None and current_id == target_id:
        return accessible

    # 2. Match by name or role string
    if isinstance(selector, str) and target_id is None:
        sel_lower = selector.strip().lower()
        node_name = (accessible.get_name() or "").lower()
        node_role = (accessible.get_role_name() or "").lower()
        node_desc = (accessible.get_description() or "").lower()

        # Exact match
        if sel_lower in (node_name, node_role, node_desc):
            return accessible

        # Prefix "role:" match e.g. "role:push button"
        if sel_lower.startswith("role:") and node_role == sel_lower[5:].strip():
            return accessible

        # Substring match in name
        if node_name and sel_lower in node_name:
            return accessible

    # Recursively check children
    for i in range(accessible.get_child_count()):
        child = accessible.get_child_at_index(i)
        if child:
            found = _find_node_by_selector(child, selector, counter)
            if found:
                return found

    return None


def perform_accessibility_action(
    app_name: str,
    element_selector: str,
    action_name: Optional[str] = None,
) -> bool:
    """Perform accessibility action (e.g. click, press, toggle) on a named element.
    
    This is completely non-disruptive: it communicates directly via D-Bus and does NOT
    move the physical mouse cursor or steal input focus.
    """
    if not HAVE_ATSPI:
        return False

    desktop = Atspi.get_desktop(0)
    target_app = None
    for i in range(desktop.get_child_count()):
        app = desktop.get_child_at_index(i)
        if app and app_name.lower() in (app.get_name() or "").lower():
            target_app = app
            break

    if not target_app:
        return False

    node = _find_node_by_selector(target_app, element_selector)
    if not node:
        return False

    try:
        act = node.get_action_iface()
        if not act:
            return False

        n_actions = act.get_n_actions()
        if n_actions == 0:
            return False

        # If action_name specified, match it
        if action_name:
            for a_idx in range(n_actions):
                if action_name.lower() in act.get_action_name(a_idx).lower():
                    return bool(act.do_action(a_idx))
        # Default to primary action (index 0)
        return bool(act.do_action(0))
    except Exception:
        return False


def set_element_value(
    app_name: str,
    element_selector: str,
    value: str,
) -> bool:
    """Set text value or numeric value on accessible element directly via AT-SPI.
    
    This is non-disruptive: it writes text directly to the accessible text widget
    without activating the window, without typing via virtual keyboard, and without
    hijacking user keyboard focus.
    """
    if not HAVE_ATSPI:
        return False

    desktop = Atspi.get_desktop(0)
    target_app = None
    for i in range(desktop.get_child_count()):
        app = desktop.get_child_at_index(i)
        if app and app_name.lower() in (app.get_name() or "").lower():
            target_app = app
            break

    if not target_app:
        return False

    node = _find_node_by_selector(target_app, element_selector)
    if not node:
        return False

    # 1. Try editable text interface
    try:
        txt = node.get_editable_text_iface()
        if txt:
            try:
                res = txt.set_text_contents(value)
                if res or res is None:
                    return True
            except Exception:
                pass

            # Alternative: delete existing text and insert
            try:
                txt.delete_text(0, -1)
                res = txt.insert_text(0, value, len(value))
                return bool(res or res is None)
            except Exception:
                pass
    except Exception:
        pass

    # 2. Try numeric/range value interface
    try:
        val = node.get_value_iface()
        if val:
            val.set_current_value(float(value))
            return True
    except Exception:
        pass

    return False
