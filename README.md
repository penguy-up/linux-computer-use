# Deepin Computer Use MCP Server

[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Deepin](https://img.shields.io/badge/Deepin%20OS-V25.2%20Wayland-0078d7.svg)](https://www.deepin.org/)
[![Compositor](https://img.shields.io/badge/Compositor-Treeland%20(wlroots)-success.svg)](https://github.com/linuxdeepin/treeland)
[![Version](https://img.shields.io/badge/version-v1.1.0-green.svg)](pyproject.toml)

English | [简体中文](README.zh-CN.md)

A production-ready [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server implementing **Computer Use** specifically tailored for **Deepin OS V25.2** running the **Treeland** Wayland compositor.

Inspired by [ilysenko/codex-desktop-linux](https://github.com/ilysenko/codex-desktop-linux) and deeply integrated with [linuxdeepin/treeland](https://github.com/linuxdeepin/treeland). Now features complete **Non-Disruptive Mode** designed so agents do not compete with or hijack the user's active keyboard focus or physical mouse cursor.

---

## Features

- **⚡ Native Wayland Screencopy**: Uses `zwlr_screencopy_manager_v1` via `grim` for ultra-fast, zero-prompt screen frame capture. Supports downscaling, cropping, bounding boxes, JPEG/PNG format selection, and payload size bounds.
- **🪟 Treeland Window Management**: Direct integration with Wayland's `zwlr_foreign_toplevel_manager_v1` via `wlrctl` to list, focus, close, maximize, and minimize active Wayland and XWayland windows.
- **🛡️ Non-Disruptive Mode (Zero-Hijack)**:
  - **AT-SPI Direct Semantic Input & Actions**: Directly inject text via `set_accessibility_text` or trigger semantic button clicks via `perform_accessibility_action` over D-Bus **without moving the physical mouse cursor or stealing active keyboard focus**.
  - **Cursor Guard**: Mouse clicks and drags accept `restore_cursor: true`, instantly snapping the physical mouse cursor back to where the user had it within milliseconds.
  - **Focus Guard**: Keyboard input and typing accept `restore_focus: true`, returning active window focus back to the user's active application after typing.
  - **Isolated Session Management**: Built-in `launch_isolated_app`, `list_isolated_apps`, and `stop_isolated_app` allow running background agent workflows in isolated environments without disturbing the primary desktop.
- **⌨️ Wayland Virtual Keyboard**: Uses `zwp_virtual_keyboard_manager_v1` via `wtype` and `wlrctl` to emit real keyboard events, complex key combinations (e.g. `Ctrl+Shift+T`, `Super`, `Alt+Tab`), and literal text without root permissions.
- **🖱️ Precision Mouse & Pointer Control**: Supports `/dev/uinput` absolute direct pointer mapping to desktop logical resolution, with fallbacks to `ydotool` and XWayland `xdotool`.
- **♿ AT-SPI Accessibility Tree**: Direct Python AT-SPI 2.0 integration to inspect running application widget hierarchies, retrieve UI element bounds, active focused window (`get_active_window`), and trigger semantic UI actions.
- **🩺 Built-in Doctor Diagnostics**: CLI and MCP tool to report environment readiness across OS version, Treeland compositor status, Wayland protocols, input permissions, and accessibility bus.
- **📦 Bundled Zero-Dependency Helpers**: Comes with self-contained, pre-tested Wayland helper binaries (`grim`, `wlrctl`, `wtype`) in `bin/`—works out of the box without requiring `sudo apt install`.

---

## Architecture Overview

```
+-------------------------------------------------------+
|              MCP Client (Claude, Codex, AGY)          |
+-------------------------------------------------------+
                           |
                     JSON-RPC (stdio)
                           v
+-------------------------------------------------------+
|             deepin-computer-use MCP Server            |
|  [Non-Disruptive: CursorGuard, FocusGuard, Isolation] |
+-------------------------------------------------------+
   |             |               |                  |
   v             v               v                  v
Screenshot   Windowing       Input Engine       AT-SPI Tree
(grim)       (wlrctl)        (wtype / uinput)   (gi.Atspi)
   |             |               |                  |
   +-------------+---------------+------------------+
                 |
                 v
   Deepin 25 Treeland Wayland Compositor & Linux Kernel
```

---

## Supported MCP Tools

| Tool Name | Description |
| :--- | :--- |
| `screenshot` | Capture screen with configurable scale, format (png/jpeg), quality, crop rect, and cursor overlay. |
| `list_windows` | Enumerate all running Wayland and XWayland toplevel windows on Treeland. |
| `get_active_window` | Get current active application and window title. |
| `focus_window` | Bring a window to front and activate focus by `app_id` or title. |
| `close_window` | Request closing a window by `app_id` or title. |
| `maximize_window` | Maximize a window. |
| `minimize_window` | Minimize a window. |
| `mouse_move` | Move cursor to absolute logical `(x, y)` coordinate. |
| `mouse_click` | Click at `(x, y)` (supports `restore_cursor` for Cursor Guard). |
| `mouse_down` / `mouse_up` | Press and release mouse buttons. |
| `mouse_drag` | Drag with mouse from start coordinate to end coordinate (supports `restore_cursor`). |
| `mouse_scroll` | Scroll vertical or horizontal mouse wheel. |
| `press_key` | Send key or hotkey combo (supports `restore_focus` for Focus Guard). |
| `type_text` | Type literal string (supports semantic `app_name`/`element` and `restore_focus`). |
| `set_accessibility_text` | **[Non-Disruptive]** Set text directly via AT-SPI without stealing focus or moving cursor. |
| `perform_accessibility_action`| **[Non-Disruptive]** Trigger semantic action (click, toggle) via AT-SPI without moving mouse. |
| `launch_isolated_app` | Launch application in an isolated environment without desktop interaction conflicts. |
| `list_isolated_apps` | List running isolated applications. |
| `stop_isolated_app` | Terminate an isolated application by PID. |
| `get_cursor_position`| Retrieve current cursor coordinate. |
| `get_screen_size` | Query desktop dimensions and resolution. |
| `list_accessible_apps`| List all applications active on Linux AT-SPI accessibility bus. |
| `get_accessibility_tree`| Extract full or application-specific UI widget hierarchy and bounds. |
| `doctor` | Output full diagnostics report on Treeland and system integration. |

---

## Quick Start

### 1. Diagnostics Check

Run the built-in doctor to inspect your environment:

```bash
python3 -m deepin_computer_use --doctor
```

### 2. Capture a Test Screenshot

```bash
python3 -m deepin_computer_use --screenshot screenshot.png
```

### 3. Configure in MCP Clients

Add to your `claude_desktop_config.json`, Codex, or Antigravity MCP settings:

```json
{
  "mcpServers": {
    "deepin-computer-use": {
      "command": "/path/to/linux-computer-use/scripts/run_server.sh",
      "args": [],
      "env": {
        "WAYLAND_DISPLAY": "treeland.socket",
        "DISPLAY": ":1"
      }
    }
  }
}
```

---

## Pointer & Hardware Permissions (Optional)

Keyboard input, window management, screenshot capture, and AT-SPI tree inspection require **no root permissions**.

If you wish to enable the direct kernel `/dev/uinput` absolute pointer for native hardware-level mouse events, run the one-time helper script:

```bash
./scripts/setup_permissions.sh
```

---

## Running Tests

```bash
pytest -v
```

---

## License

Licensed under the [Apache-2.0 License](LICENSE).
