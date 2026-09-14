"""Treeland Wayland toplevel window management."""

from __future__ import annotations

import os
import subprocess
from typing import Any, Dict, List, Optional

from ..config import WAYLAND_DISPLAY, WLRCTL_BIN, XDG_RUNTIME_DIR
from .dde_dock import activate_dock_app


def list_windows() -> List[Dict[str, Any]]:
    """List all toplevel windows on Treeland compositor."""
    windows: List[Dict[str, Any]] = []
    wlrctl = WLRCTL_BIN or "wlrctl"
    env = dict(os.environ)
    env["WAYLAND_DISPLAY"] = WAYLAND_DISPLAY
    env["XDG_RUNTIME_DIR"] = XDG_RUNTIME_DIR

    try:
        res = subprocess.run(
            [wlrctl, "toplevel", "list"],
            env=env,
            capture_output=True,
            text=True,
            timeout=3,
        )
        if res.returncode == 0:
            for idx, line in enumerate(res.stdout.splitlines()):
                line = line.strip()
                if not line:
                    continue
                if ": " in line:
                    app_id, title = line.split(": ", 1)
                else:
                    app_id, title = line, ""
                windows.append({
                    "id": idx + 1,
                    "app_id": app_id.strip(),
                    "title": title.strip(),
                    "backend": "treeland",
                })
            return windows
    except Exception:
        pass

    # Fallback: wmctrl -l
    try:
        res = subprocess.run(["wmctrl", "-l", "-x"], capture_output=True, text=True, timeout=2)
        if res.returncode == 0:
            for line in res.stdout.splitlines():
                parts = line.split(maxsplit=4)
                if len(parts) >= 5:
                    wid, desk, wm_class, client, title = parts
                    windows.append({
                        "id": wid,
                        "app_id": wm_class.split(".")[0],
                        "title": title.strip(),
                        "backend": "xwayland",
                    })
    except Exception:
        pass

    return windows


def focus_window(target: str) -> bool:
    """Focus/activate a window by app_id or title substring."""
    target_clean = target.strip()
    if not target_clean:
        return False

    wlrctl = WLRCTL_BIN or "wlrctl"
    env = dict(os.environ)
    env["WAYLAND_DISPLAY"] = WAYLAND_DISPLAY
    env["XDG_RUNTIME_DIR"] = XDG_RUNTIME_DIR

    # 1. First find window to get exact match
    windows = list_windows()
    matched_app_id = None
    matched_title = None

    for win in windows:
        if target_clean.lower() in win["app_id"].lower():
            matched_app_id = win["app_id"]
            matched_title = win["title"]
            break
        elif target_clean.lower() in win["title"].lower():
            matched_app_id = win["app_id"]
            matched_title = win["title"]
            break

    # 2. Try wlrctl toplevel focus
    candidates = []
    if matched_app_id:
        candidates.append(f"app_id:{matched_app_id}")
    if matched_title:
        candidates.append(f"title:{matched_title}")
    candidates.append(f"app_id:{target_clean}")
    candidates.append(f"title:{target_clean}")

    for selector in candidates:
        try:
            res = subprocess.run(
                [wlrctl, "toplevel", "focus", selector],
                env=env,
                capture_output=True,
                timeout=2,
            )
            if res.returncode == 0:
                return True
        except Exception:
            pass

    # 3. Try DDE Dock activate fallback
    if matched_app_id and activate_dock_app(matched_app_id):
        return True

    # 4. Fallback to wmctrl -a
    try:
        res = subprocess.run(["wmctrl", "-a", target_clean], capture_output=True, timeout=2)
        if res.returncode == 0:
            return True
    except Exception:
        pass

    return False


def close_window(target: str) -> bool:
    """Close a window by app_id or title substring."""
    target_clean = target.strip()
    wlrctl = WLRCTL_BIN or "wlrctl"
    env = dict(os.environ)
    env["WAYLAND_DISPLAY"] = WAYLAND_DISPLAY
    env["XDG_RUNTIME_DIR"] = XDG_RUNTIME_DIR

    windows = list_windows()
    matched_app_id = None
    for win in windows:
        if target_clean.lower() in win["app_id"].lower() or target_clean.lower() in win["title"].lower():
            matched_app_id = win["app_id"]
            break

    selector = f"app_id:{matched_app_id or target_clean}"
    try:
        res = subprocess.run(
            [wlrctl, "toplevel", "close", selector],
            env=env,
            capture_output=True,
            timeout=2,
        )
        return res.returncode == 0
    except Exception:
        return False


def maximize_window(target: str) -> bool:
    """Maximize a window by app_id or title."""
    wlrctl = WLRCTL_BIN or "wlrctl"
    env = dict(os.environ)
    env["WAYLAND_DISPLAY"] = WAYLAND_DISPLAY
    env["XDG_RUNTIME_DIR"] = XDG_RUNTIME_DIR
    try:
        res = subprocess.run(
            [wlrctl, "toplevel", "maximize", f"app_id:{target}"],
            env=env,
            capture_output=True,
            timeout=2,
        )
        return res.returncode == 0
    except Exception:
        return False


def minimize_window(target: str) -> bool:
    """Minimize a window by app_id or title."""
    wlrctl = WLRCTL_BIN or "wlrctl"
    env = dict(os.environ)
    env["WAYLAND_DISPLAY"] = WAYLAND_DISPLAY
    env["XDG_RUNTIME_DIR"] = XDG_RUNTIME_DIR
    try:
        res = subprocess.run(
            [wlrctl, "toplevel", "minimize", f"app_id:{target}"],
            env=env,
            capture_output=True,
            timeout=2,
        )
        return res.returncode == 0
    except Exception:
        return False
