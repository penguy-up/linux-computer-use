"""AT-SPI2 accessibility integration for Deepin Linux desktop."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

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


def _node_to_dict(accessible: Any, current_depth: int, max_depth: int, node_counter: List[int], max_nodes: int) -> Optional[Dict[str, Any]]:
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
            states_str = state_set.get_states()
            # Common useful states
            for s in ("focused", "visible", "showing", "enabled", "focusable", "checked", "selectable"):
                if state_set.contains(getattr(Atspi.StateType, s.upper(), None)):
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


def _find_node_by_id_or_name(accessible: Any, selector: str | int) -> Optional[Any]:
    """Helper to locate an AtspiAccessible by index, id, or name."""
    if isinstance(selector, str) and (accessible.get_name() or "").lower() == selector.lower():
        return accessible

    for i in range(accessible.get_child_count()):
        child = accessible.get_child_at_index(i)
        if child:
            found = _find_node_by_id_or_name(child, selector)
            if found:
                return found
    return None


def perform_accessibility_action(
    app_name: str,
    element_selector: str,
    action_name: Optional[str] = None,
) -> bool:
    """Perform accessibility action (e.g. click, press, toggle) on a named element."""
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

    node = _find_node_by_id_or_name(target_app, element_selector)
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
                    return act.do_action(a_idx)
        # Default to primary action (index 0)
        return act.do_action(0)
    except Exception:
        return False


def set_element_value(
    app_name: str,
    element_selector: str,
    value: str,
) -> bool:
    """Set text value or numeric value on accessible element."""
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

    node = _find_node_by_id_or_name(target_app, element_selector)
    if not node:
        return False

    # Try editable text first
    try:
        txt = node.get_editable_text_iface()
        if txt:
            txt.set_text_contents(value)
            return True
    except Exception:
        pass

    # Try value interface
    try:
        val = node.get_value_iface()
        if val:
            val.set_current_value(float(value))
            return True
    except Exception:
        pass

    return False
