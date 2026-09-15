# Deepin Computer Use MCP Server

[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Deepin](https://img.shields.io/badge/Deepin%20OS-V25.2%20Wayland-0078d7.svg)](https://www.deepin.org/)
[![Compositor](https://img.shields.io/badge/Compositor-Treeland%20(wlroots)-success.svg)](https://github.com/linuxdeepin/treeland)

English | [简体中文](README.zh-CN.md)

A production-ready [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server implementing **Computer Use** specifically tailored for **Deepin OS V25.2** running the **Treeland** Wayland compositor.

Inspired by [ilysenko/codex-desktop-linux](https://github.com/ilysenko/codex-desktop-linux) and deeply integrated with [linuxdeepin/treeland](https://github.com/linuxdeepin/treeland).

---

## Features

- **⚡ Native Wayland Screencopy**: Uses `zwlr_screencopy_manager_v1` via `grim` for ultra-fast, zero-prompt screen frame capture. Supports downscaling, cropping, bounding boxes, JPEG/PNG format selection, and payload size bounds.
- **🪟 Treeland Window Management**: Direct integration with Wayland's `zwlr_foreign_toplevel_manager_v1` via `wlrctl` to list, focus, close, maximize, and minimize active Wayland and XWayland windows.
- **⌨️ Wayland Virtual Keyboard**: Uses `zwp_virtual_keyboard_manager_v1` via `wtype` and `wlrctl` to emit real keyboard events, complex key combinations (e.g. `Ctrl+Shift+T`, `Super`, `Alt+Tab`), and literal text without root permissions.
- **🖱️ Precision Mouse & Pointer Control**: Supports `/dev/uinput` absolute direct pointer mapping to desktop logical resolution, with fallbacks to `ydotool` and XWayland `xdotool`.
- **♿ AT-SPI Accessibility Tree**: Direct Python AT-SPI 2.0 integration to inspect running application widget hierarchies, retrieve UI element bounds, and trigger semantic UI actions (clicks, toggles, text edits) directly.
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
| `focus_window` | Bring a window to front and activate focus by `app_id` or title. |
| `close_window` | Request closing a window by `app_id` or title. |
| `maximize_window` | Maximize a window. |
| `minimize_window` | Minimize a window. |
| `mouse_move` | Move cursor to absolute logical `(x, y)` coordinate. |
| `mouse_click` | Click at `(x, y)` (supports `left`, `right`, `middle`, single/double/triple clicks). |
| `mouse_down` / `mouse_up` | Press and release mouse buttons. |
| `mouse_drag` | Drag with mouse from start coordinate to end coordinate. |
| `mouse_scroll` | Scroll vertical or horizontal mouse wheel. |
| `press_key` | Send key or hotkey combo (e.g. `ctrl+c`, `alt+tab`, `Return`, `Super`). |
| `type_text` | Type literal string into focused element. |
| `get_cursor_position`| Retrieve current cursor coordinate. |
| `get_screen_size` | Query desktop dimensions and resolution. |
| `list_accessible_apps`| List all applications active on Linux AT-SPI accessibility bus. |
| `get_accessibility_tree`| Extract full or application-specific UI widget hierarchy and bounds. |
| `perform_accessibility_action`| Trigger semantic accessibility action (click, toggle) on target element. |
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
pytest -v tests/
```

---

## License

Licensed under the [Apache-2.0 License](LICENSE).
