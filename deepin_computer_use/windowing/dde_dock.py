"""Deepin DDE TaskManager / Dock DBus integration."""

from __future__ import annotations

import subprocess
from typing import Any, Dict, List


def list_dock_apps() -> List[Dict[str, Any]]:
    """List running or docked applications registered with DDE Dock TaskManager."""
    apps: List[Dict[str, Any]] = []
    try:
        res = subprocess.run(
            ["busctl", "--user", "tree", "org.deepin.ds.Dock"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if res.returncode != 0:
            return apps

        prefix = "/org/deepin/ds/Dock/TaskManager/Item/AppItem/"
        for line in res.stdout.splitlines():
            if prefix in line:
                idx = line.find(prefix)
                obj_path = line[idx:].strip()
                app_name = obj_path.split("/")[-1].replace("_2d", "-").replace("_2e", ".")
                apps.append({
                    "app_id": app_name,
                    "dbus_path": obj_path,
                })
    except Exception:
        pass
    return apps


def activate_dock_app(app_id: str) -> bool:
    """Activate an application via DDE Dock TaskManager."""
    clean_id = app_id.replace("-", "_2d").replace(".", "_2e")
    obj_path = f"/org/deepin/ds/Dock/TaskManager/Item/AppItem/{clean_id}"
    try:
        res = subprocess.run(
            [
                "busctl",
                "--user",
                "call",
                "org.deepin.ds.Dock",
                obj_path,
                "org.deepin.ds.Dock.TaskManager.Item",
                "handleClick",
                "s",
                "activate",
            ],
            capture_output=True,
            timeout=2,
        )
        return res.returncode == 0
    except Exception:
        return False
