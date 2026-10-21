"""Isolated application and headless display session management."""

from __future__ import annotations

import logging
import os
import shlex
import subprocess
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger("deepin_computer_use.isolation")

# In-memory registry of isolated processes: pid -> dict
_ISOLATED_APPS: Dict[int, Dict[str, Any]] = {}


def list_isolated_apps() -> List[Dict[str, Any]]:
    """List all active isolated/sandboxed applications started through this module."""
    active = []
    dead = []
    for pid, info in _ISOLATED_APPS.items():
        proc: subprocess.Popen = info.get("process")
        if proc and proc.poll() is None:
            active.append({
                "pid": pid,
                "command": info["command"],
                "app_id": info.get("app_id"),
                "display": info.get("display"),
                "start_time": info.get("start_time"),
                "status": "running",
            })
        else:
            dead.append(pid)

    for pid in dead:
        _ISOLATED_APPS.pop(pid, None)

    return active


def launch_isolated_app(
    command: str,
    app_id: Optional[str] = None,
    isolated_display: Optional[str] = None,
    extra_env: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Launch an application in an isolated environment.
    
    Args:
        command: Command string to execute (e.g. 'google-chrome --new-window').
        app_id: Optional application identifier tag.
        isolated_display: Optional custom WAYLAND_DISPLAY socket. If omitted, uses current display.
        extra_env: Additional environment variables to pass to the isolated process.
        
    Returns:
        Dictionary containing process PID, command, and status.
    """
    env = dict(os.environ)
    if isolated_display:
        env["WAYLAND_DISPLAY"] = isolated_display
    if extra_env:
        env.update(extra_env)

    # Ensure application doesn't inherit background session conflicts
    args = shlex.split(command)
    try:
        proc = subprocess.Popen(
            args,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
    except Exception as e:
        logger.error(f"Failed to launch isolated app '{command}': {e}")
        return {
            "success": False,
            "error": str(e),
        }

    info = {
        "pid": proc.pid,
        "command": command,
        "app_id": app_id or (args[0] if args else ""),
        "display": env.get("WAYLAND_DISPLAY", ""),
        "start_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "process": proc,
    }
    _ISOLATED_APPS[proc.pid] = info

    return {
        "success": True,
        "pid": proc.pid,
        "command": command,
        "display": info["display"],
        "status": "started",
    }


def stop_isolated_app(pid: int, timeout: float = 3.0) -> bool:
    """Terminate an isolated application by PID."""
    info = _ISOLATED_APPS.get(pid)
    if not info:
        # Check if process is still running anyway
        try:
            os.kill(pid, 0)
        except OSError:
            return True  # Already dead

        try:
            os.kill(pid, 15)  # SIGTERM
            return True
        except Exception:
            return False

    proc: subprocess.Popen = info.get("process")
    if proc:
        try:
            proc.terminate()
            try:
                proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=1.0)
            _ISOLATED_APPS.pop(pid, None)
            return True
        except Exception as e:
            logger.error(f"Error terminating isolated app {pid}: {e}")
            return False

    return False
