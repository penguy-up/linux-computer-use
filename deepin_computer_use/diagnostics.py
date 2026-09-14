"""System integration diagnostics and health check (Doctor) for Deepin OS V25."""

from __future__ import annotations

import os
import platform
import subprocess
from typing import Any, Dict, List

from .config import (
    DISPLAY,
    GRIM_BIN,
    WAYLAND_DISPLAY,
    WLRCTL_BIN,
    WTYPE_BIN,
    XDOTOOL_BIN,
    XDG_RUNTIME_DIR,
)


def doctor_report() -> Dict[str, Any]:
    """Run full system integration readiness check for Deepin Computer Use."""
    checks: List[Dict[str, Any]] = []

    # 1. OS Release
    os_name = "Unknown"
    os_version = "Unknown"
    if os.path.exists("/etc/os-release"):
        with open("/etc/os-release", "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("PRETTY_NAME="):
                    os_name = line.split("=", 1)[1].strip().strip('"')
                elif line.startswith("VERSION="):
                    os_version = line.split("=", 1)[1].strip().strip('"')

    is_deepin = "deepin" in os_name.lower() or "deepin" in os_version.lower()
    checks.append({
        "component": "Operating System",
        "status": "PASS" if is_deepin else "WARN",
        "detail": f"{os_name} (Kernel {platform.release()})",
    })

    # 2. Wayland & Compositor
    treeland_running = False
    try:
        ps_res = subprocess.run(["ps", "-ef"], capture_output=True, text=True, timeout=2)
        treeland_running = "treeland" in ps_res.stdout
    except Exception:
        pass

    checks.append({
        "component": "Compositor (Treeland)",
        "status": "PASS" if treeland_running else "WARN",
        "detail": f"Treeland active: {treeland_running}, WAYLAND_DISPLAY={WAYLAND_DISPLAY}",
    })

    # 3. Screencopy / Grim
    grim_ok = False
    grim_detail = "grim not found"
    if GRIM_BIN:
        try:
            res = subprocess.run([GRIM_BIN, "-h"], capture_output=True, timeout=2)
            if res.returncode in (0, 1):
                grim_ok = True
                grim_detail = f"Found at {GRIM_BIN}"
        except Exception as e:
            grim_detail = f"Error: {e}"

    checks.append({
        "component": "Screenshot (zwlr_screencopy)",
        "status": "PASS" if grim_ok else "FAIL",
        "detail": grim_detail,
    })

    # 4. Window Management (wlrctl)
    wlrctl_ok = False
    wlrctl_detail = "wlrctl not found"
    if WLRCTL_BIN:
        try:
            res = subprocess.run([WLRCTL_BIN, "toplevel", "list"], capture_output=True, text=True, timeout=3)
            if res.returncode == 0:
                count = len(res.stdout.splitlines())
                wlrctl_ok = True
                wlrctl_detail = f"Found at {WLRCTL_BIN} (Detected {count} toplevel windows)"
        except Exception as e:
            wlrctl_detail = f"Error: {e}"

    checks.append({
        "component": "Window Management (zwlr_foreign_toplevel)",
        "status": "PASS" if wlrctl_ok else "FAIL",
        "detail": wlrctl_detail,
    })

    # 5. Virtual Keyboard (wtype)
    wtype_ok = False
    wtype_detail = "wtype not found"
    if WTYPE_BIN:
        try:
            res = subprocess.run([WTYPE_BIN, "-k", "Return"], capture_output=True, timeout=2)
            if res.returncode == 0:
                wtype_ok = True
                wtype_detail = f"Found at {WTYPE_BIN} (Wayland virtual keyboard operational)"
        except Exception as e:
            wtype_detail = f"Error: {e}"

    checks.append({
        "component": "Keyboard Input (zwp_virtual_keyboard)",
        "status": "PASS" if wtype_ok else "FAIL",
        "detail": wtype_detail,
    })

    # 6. Pointer / UInput
    uinput_ok = os.access("/dev/uinput", os.W_OK)
    uinput_detail = "Writable" if uinput_ok else "Not writable without root permissions"
    checks.append({
        "component": "Mouse Pointer (/dev/uinput)",
        "status": "PASS" if uinput_ok else "WARN",
        "detail": uinput_detail,
        "recommendation": (
            "Run `scripts/setup_permissions.sh` or `sudo usermod -aG input $USER` to enable direct hardware pointer."
            if not uinput_ok
            else "Direct absolute pointer fully enabled."
        ),
    })

    # 7. AT-SPI Accessibility Bus
    atspi_ok = False
    atspi_detail = "Not available"
    try:
        from .atspi import list_accessible_apps
        apps = list_accessible_apps()
        atspi_ok = len(apps) > 0
        atspi_detail = f"Connected ({len(apps)} accessible applications found)"
    except Exception as e:
        atspi_detail = f"Error: {e}"

    checks.append({
        "component": "Accessibility (AT-SPI 2.0)",
        "status": "PASS" if atspi_ok else "WARN",
        "detail": atspi_detail,
    })

    # Overall Status
    failures = [c for c in checks if c["status"] == "FAIL"]
    warnings = [c for c in checks if c["status"] == "WARN"]

    if failures:
        overall = "UNHEALTHY"
    elif warnings:
        overall = "READY_WITH_WARNINGS"
    else:
        overall = "HEALTHY"

    return {
        "status": overall,
        "checks": checks,
        "wayland_display": WAYLAND_DISPLAY,
        "display": DISPLAY,
        "runtime_dir": XDG_RUNTIME_DIR,
    }


def format_doctor_report(report: Dict[str, Any]) -> str:
    """Format doctor report into readable Markdown."""
    lines = [
        f"# Deepin Computer Use Diagnostics (Status: {report['status']})",
        "",
        f"- **WAYLAND_DISPLAY**: `{report['wayland_display']}`",
        f"- **DISPLAY**: `{report['display']}`",
        f"- **XDG_RUNTIME_DIR**: `{report['runtime_dir']}`",
        "",
        "## Component Checks",
        "",
        "| Component | Status | Details |",
        "| :--- | :---: | :--- |",
    ]
    for c in report["checks"]:
        icon = "✅ PASS" if c["status"] == "PASS" else ("⚠️ WARN" if c["status"] == "WARN" else "❌ FAIL")
        rec = f" <br>*Note: {c['recommendation']}*" if "recommendation" in c else ""
        lines.append(f"| {c['component']} | {icon} | {c['detail']}{rec} |")

    return "\n".join(lines)
