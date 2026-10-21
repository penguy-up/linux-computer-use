"""Model Context Protocol (MCP) Server for Deepin OS V25 (Treeland Wayland)."""

from __future__ import annotations

import asyncio
import json
import logging
import sys
import traceback
from typing import Any, Callable, Coroutine, Dict, List, Optional

from .atspi import (
    get_accessibility_tree,
    get_active_window,
    list_accessible_apps,
    perform_accessibility_action,
    set_element_value,
)
from .diagnostics import doctor_report, format_doctor_report
from .input import (
    get_cursor_position,
    mouse_click,
    mouse_down,
    mouse_drag,
    mouse_move,
    mouse_scroll,
    mouse_up,
    press_key,
    release_all_buttons,
    type_text,
)
from .isolation import (
    launch_isolated_app,
    list_isolated_apps,
    stop_isolated_app,
)
from .screenshot import capture_screenshot, get_screen_size
from .windowing import (
    close_window,
    focus_window,
    list_windows,
    maximize_window,
    minimize_window,
)

logger = logging.getLogger("deepin_computer_use")

SERVER_NAME = "deepin-computer-use"
SERVER_VERSION = "1.1.0"
PROTOCOL_VERSION = "2024-11-05"


TOOLS_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "name": "screenshot",
        "description": "Capture the Wayland screen and return a viewable, size-bounded image with coordinate metadata.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "max_width": {
                    "type": "integer",
                    "description": "Maximum width for the returned image (default: 1920).",
                },
                "max_height": {
                    "type": "integer",
                    "description": "Maximum height for the returned image (default: 1080).",
                },
                "scale": {
                    "type": "number",
                    "description": "Optional explicit scaling factor, e.g. 0.5 for half resolution.",
                },
                "format": {
                    "type": "string",
                    "enum": ["png", "jpeg"],
                    "description": "Image format ('png' or 'jpeg', default: 'png').",
                },
                "quality": {
                    "type": "integer",
                    "description": "JPEG quality from 1 to 95 (default: 80).",
                },
                "crop_rect": {
                    "type": "object",
                    "properties": {
                        "x": {"type": "integer"},
                        "y": {"type": "integer"},
                        "width": {"type": "integer"},
                        "height": {"type": "integer"},
                    },
                    "required": ["x", "y", "width", "height"],
                    "description": "Optional bounding box to crop before scaling.",
                },
                "include_cursor": {
                    "type": "boolean",
                    "description": "Whether to draw mouse cursor in screenshot (default: false).",
                },
            },
        },
    },
    {
        "name": "list_windows",
        "description": "List all active desktop windows on Treeland compositor with their app_id and titles.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "get_active_window",
        "description": "Get the application name and window title of the currently focused/active desktop window.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "focus_window",
        "description": "Activate and bring a window to the front using app_id or window title substring.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "The app_id (e.g. 'google-chrome') or title substring (e.g. 'Chrome').",
                },
            },
            "required": ["target"],
        },
    },
    {
        "name": "close_window",
        "description": "Close a window by app_id or title substring.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "The app_id or title of the window to close.",
                },
            },
            "required": ["target"],
        },
    },
    {
        "name": "maximize_window",
        "description": "Maximize a window by app_id.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "The app_id of the window."},
            },
            "required": ["target"],
        },
    },
    {
        "name": "minimize_window",
        "description": "Minimize a window by app_id.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "The app_id of the window."},
            },
            "required": ["target"],
        },
    },
    {
        "name": "mouse_move",
        "description": "Move the mouse cursor to absolute screen coordinates (x, y).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "x": {"type": "integer", "description": "Target X coordinate in pixels."},
                "y": {"type": "integer", "description": "Target Y coordinate in pixels."},
            },
            "required": ["x", "y"],
        },
    },
    {
        "name": "mouse_click",
        "description": "Click the mouse at current or specified coordinate.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "x": {"type": "integer", "description": "Optional X coordinate to click."},
                "y": {"type": "integer", "description": "Optional Y coordinate to click."},
                "button": {
                    "type": "string",
                    "enum": ["left", "right", "middle"],
                    "description": "Mouse button to click (default: 'left').",
                },
                "count": {
                    "type": "integer",
                    "description": "Click count (1 for single, 2 for double, 3 for triple; default: 1).",
                },
                "restore_cursor": {
                    "type": "boolean",
                    "description": "If true, snap cursor back to its previous position immediately after clicking (Cursor Guard) to avoid hijacking user cursor.",
                },
            },
        },
    },
    {
        "name": "mouse_down",
        "description": "Press and hold a mouse button.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "button": {
                    "type": "string",
                    "enum": ["left", "right", "middle"],
                    "description": "Mouse button to press down (default: 'left').",
                },
            },
        },
    },
    {
        "name": "mouse_up",
        "description": "Release a previously held mouse button.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "button": {
                    "type": "string",
                    "enum": ["left", "right", "middle"],
                    "description": "Mouse button to release (default: 'left').",
                },
            },
        },
    },
    {
        "name": "release_all_buttons",
        "description": "Release all mouse buttons that are currently marked as held down (safety cleanup).",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "mouse_drag",
        "description": "Click, drag from (start_x, start_y) to (end_x, end_y), and release.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "start_x": {"type": "integer", "description": "Start X coordinate."},
                "start_y": {"type": "integer", "description": "Start Y coordinate."},
                "end_x": {"type": "integer", "description": "End X coordinate."},
                "end_y": {"type": "integer", "description": "End Y coordinate."},
                "button": {
                    "type": "string",
                    "enum": ["left", "right", "middle"],
                    "description": "Button to drag with (default: 'left').",
                },
                "restore_cursor": {
                    "type": "boolean",
                    "description": "If true, snap cursor back to start coordinate after drag completes (Cursor Guard).",
                },
            },
            "required": ["start_x", "start_y", "end_x", "end_y"],
        },
    },
    {
        "name": "mouse_scroll",
        "description": "Scroll mouse wheel vertically or horizontally.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "direction": {
                    "type": "string",
                    "enum": ["up", "down", "left", "right"],
                    "description": "Scroll direction (default: 'down').",
                },
                "amount": {
                    "type": "integer",
                    "description": "Number of scroll steps/clicks (default: 2).",
                },
            },
        },
    },
    {
        "name": "press_key",
        "description": "Press a key or key combination (e.g. 'Ctrl+C', 'Super', 'Alt+Tab', 'Return', 'Escape').",
        "inputSchema": {
            "type": "object",
            "properties": {
                "key_combo": {
                    "type": "string",
                    "description": "Key or combo, joined by '+'. E.g. 'ctrl+c', 'Return', 'alt+F4', 'super'.",
                },
                "restore_focus": {
                    "type": "boolean",
                    "description": "If true, restore active window focus back to user's window after pressing key (Focus Guard).",
                },
            },
            "required": ["key_combo"],
        },
    },
    {
        "name": "type_text",
        "description": "Type literal text into the focused window or direct to an accessible element.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "The text to type."},
                "delay_ms": {
                    "type": "integer",
                    "description": "Inter-character delay in milliseconds (default: 10).",
                },
                "method": {
                    "type": "string",
                    "enum": ["auto", "atspi", "type", "clipboard"],
                    "description": "Typing method: 'auto' (default), 'atspi' (semantic direct injection without stealing focus), 'type' (keystroke emulation), or 'clipboard' (Ctrl+V).",
                },
                "app_name": {
                    "type": "string",
                    "description": "Optional application name for direct semantic AT-SPI typing without stealing focus.",
                },
                "element": {
                    "type": "string",
                    "description": "Optional element name, selector, or node ID for direct semantic AT-SPI typing.",
                },
                "restore_focus": {
                    "type": "boolean",
                    "description": "If true, restore active window focus back to user's window after typing (Focus Guard).",
                },
            },
            "required": ["text"],
        },
    },
    {
        "name": "set_accessibility_text",
        "description": "Set text directly on an editable element via AT-SPI accessibility bus. Completely non-disruptive: does NOT move physical mouse cursor and does NOT steal window focus.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "app_name": {
                    "type": "string",
                    "description": "Application name on AT-SPI bus (e.g. 'deepin-editor', 'google-chrome').",
                },
                "element": {
                    "type": "string",
                    "description": "Element name, selector, or numeric node ID.",
                },
                "text": {
                    "type": "string",
                    "description": "Text value to set into the element.",
                },
            },
            "required": ["app_name", "element", "text"],
        },
    },
    {
        "name": "get_cursor_position",
        "description": "Get current mouse cursor coordinate (x, y).",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "get_screen_size",
        "description": "Get logical / physical desktop dimensions.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "list_accessible_apps",
        "description": "List all applications registered on the Linux AT-SPI accessibility bus.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "get_accessibility_tree",
        "description": "Get accessibility node tree (widgets, buttons, labels, coordinates) for an app or whole desktop.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "app_name": {
                    "type": "string",
                    "description": "Optional target application name (e.g. 'Chrome', 'Editor').",
                },
                "max_depth": {
                    "type": "integer",
                    "description": "Maximum tree depth to traverse (default: 4).",
                },
                "max_nodes": {
                    "type": "integer",
                    "description": "Maximum number of nodes to return (default: 150).",
                },
            },
        },
    },
    {
        "name": "perform_accessibility_action",
        "description": "Perform a semantic action (e.g. click, press) directly on an accessible element without moving the physical mouse or stealing window focus.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "app_name": {"type": "string", "description": "Application name."},
                "element": {"type": "string", "description": "Element name, label, or node ID."},
                "action": {"type": "string", "description": "Action name (e.g. 'click', default: primary action)."},
            },
            "required": ["app_name", "element"],
        },
    },
    {
        "name": "launch_isolated_app",
        "description": "Launch an application in an isolated environment/display so it runs without conflicting with active desktop windows.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Shell command to run (e.g. 'google-chrome --new-window').",
                },
                "app_id": {
                    "type": "string",
                    "description": "Optional application identifier.",
                },
                "isolated_display": {
                    "type": "string",
                    "description": "Optional custom WAYLAND_DISPLAY socket.",
                },
            },
            "required": ["command"],
        },
    },
    {
        "name": "list_isolated_apps",
        "description": "List all active isolated applications running in background sandboxes.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "stop_isolated_app",
        "description": "Stop/terminate a running isolated application by PID.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "pid": {
                    "type": "integer",
                    "description": "Process ID of the isolated application to terminate.",
                },
            },
            "required": ["pid"],
        },
    },
    {
        "name": "doctor",
        "description": "Run Deepin V25 Wayland (Treeland) integration health diagnostics.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
]


class MCPServer:
    """Async MCP Server implementation over standard I/O."""

    def __init__(self):
        self.tools = {tool["name"]: tool for tool in TOOLS_DEFINITIONS}

    async def handle_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        req_id = request.get("id")
        method = request.get("method")
        params = request.get("params", {})

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {
                        "tools": {
                            "listChanged": False,
                        },
                    },
                    "serverInfo": {
                        "name": SERVER_NAME,
                        "version": SERVER_VERSION,
                    },
                },
            }

        elif method == "notifications/initialized":
            return None

        elif method == "ping":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {},
            }

        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "tools": TOOLS_DEFINITIONS,
                },
            }

        elif method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})

            if tool_name not in self.tools:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: '{tool_name}'",
                    },
                }

            try:
                res = await self.execute_tool(tool_name, tool_args)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": res,
                }
            except Exception as e:
                logger.error(f"Error executing tool '{tool_name}': {e}\n{traceback.format_exc()}")
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": f"Error executing {tool_name}: {e}",
                            }
                        ],
                        "isError": True,
                    },
                }

        else:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32601,
                    "message": f"Unhandled method: {method}",
                },
            }

    async def execute_tool(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the requested tool and format result in MCP Content format."""
        if name == "screenshot":
            max_w = int(args.get("max_width", 1920))
            max_h = int(args.get("max_height", 1080))
            scale = args.get("scale")
            if scale is not None:
                scale = float(scale)
            fmt = args.get("format", "png")
            quality = int(args.get("quality", 80))
            crop_rect = args.get("crop_rect")
            include_cursor = bool(args.get("include_cursor", False))

            data_b64, mime_type, meta = await asyncio.to_thread(
                capture_screenshot,
                max_width=max_w,
                max_height=max_h,
                scale=scale,
                format=fmt,
                quality=quality,
                crop_rect=crop_rect,
                include_cursor=include_cursor,
            )

            return {
                "content": [
                    {
                        "type": "image",
                        "data": data_b64,
                        "mimeType": mime_type,
                    },
                    {
                        "type": "text",
                        "text": json.dumps(meta, indent=2),
                    },
                ],
                "isError": False,
            }

        elif name == "list_windows":
            windows = await asyncio.to_thread(list_windows)
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(windows, ensure_ascii=False, indent=2),
                    }
                ],
                "isError": False,
            }

        elif name == "get_active_window":
            app, win = await asyncio.to_thread(get_active_window)
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps({"active_app": app, "active_window": win}, ensure_ascii=False, indent=2),
                    }
                ],
                "isError": False,
            }

        elif name == "focus_window":
            target = args["target"]
            ok = await asyncio.to_thread(focus_window, target)
            return {
                "content": [{"type": "text", "text": f"Focus window '{target}': {'Success' if ok else 'Failed'}"}],
                "isError": not ok,
            }

        elif name == "close_window":
            target = args["target"]
            ok = await asyncio.to_thread(close_window, target)
            return {
                "content": [{"type": "text", "text": f"Close window '{target}': {'Success' if ok else 'Failed'}"}],
                "isError": not ok,
            }

        elif name == "maximize_window":
            target = args["target"]
            ok = await asyncio.to_thread(maximize_window, target)
            return {
                "content": [{"type": "text", "text": f"Maximize window '{target}': {'Success' if ok else 'Failed'}"}],
                "isError": not ok,
            }

        elif name == "minimize_window":
            target = args["target"]
            ok = await asyncio.to_thread(minimize_window, target)
            return {
                "content": [{"type": "text", "text": f"Minimize window '{target}': {'Success' if ok else 'Failed'}"}],
                "isError": not ok,
            }

        elif name == "mouse_move":
            x = int(args["x"])
            y = int(args["y"])
            await asyncio.to_thread(mouse_move, x, y)
            return {
                "content": [{"type": "text", "text": f"Moved cursor to ({x}, {y})"}],
                "isError": False,
            }

        elif name == "mouse_click":
            x = args.get("x")
            y = args.get("y")
            if x is not None:
                x = int(x)
            if y is not None:
                y = int(y)
            btn = args.get("button", "left")
            cnt = int(args.get("count", 1))
            restore_cursor = bool(args.get("restore_cursor", False))

            await asyncio.to_thread(mouse_click, x, y, btn, cnt, restore_cursor)
            info = f"Clicked {btn} button {cnt} time(s)"
            if x is not None and y is not None:
                info += f" at ({x}, {y})"
            if restore_cursor:
                info += " [Cursor Guard: cursor restored]"
            return {
                "content": [{"type": "text", "text": info}],
                "isError": False,
            }

        elif name == "mouse_down":
            btn = args.get("button", "left")
            await asyncio.to_thread(mouse_down, btn)
            return {
                "content": [{"type": "text", "text": f"Mouse button '{btn}' down"}],
                "isError": False,
            }

        elif name == "mouse_up":
            btn = args.get("button", "left")
            await asyncio.to_thread(mouse_up, btn)
            return {
                "content": [{"type": "text", "text": f"Mouse button '{btn}' up"}],
                "isError": False,
            }

        elif name == "release_all_buttons":
            released = await asyncio.to_thread(release_all_buttons)
            info = f"Released buttons: {released}" if released else "All mouse buttons were already released"
            return {
                "content": [{"type": "text", "text": info}],
                "isError": False,
            }

        elif name == "mouse_drag":
            sx = int(args["start_x"])
            sy = int(args["start_y"])
            ex = int(args["end_x"])
            ey = int(args["end_y"])
            btn = args.get("button", "left")
            restore_cursor = bool(args.get("restore_cursor", False))
            await asyncio.to_thread(mouse_drag, sx, sy, ex, ey, btn, 10, 20, restore_cursor)
            info = f"Dragged from ({sx}, {sy}) to ({ex}, {ey})"
            if restore_cursor:
                info += " [Cursor Guard: cursor restored]"
            return {
                "content": [{"type": "text", "text": info}],
                "isError": False,
            }

        elif name == "mouse_scroll":
            direction = args.get("direction", "down")
            amount = int(args.get("amount", 2))
            await asyncio.to_thread(mouse_scroll, direction, amount)
            return {
                "content": [{"type": "text", "text": f"Scrolled {direction} by {amount} units"}],
                "isError": False,
            }

        elif name == "press_key":
            combo = args["key_combo"]
            restore_focus = bool(args.get("restore_focus", False))
            ok = await asyncio.to_thread(press_key, combo, restore_focus)
            info = f"Pressed key '{combo}'"
            if restore_focus:
                info += " [Focus Guard: window focus restored]"
            return {
                "content": [{"type": "text", "text": info}],
                "isError": False,
            }

        elif name == "type_text":
            text = args["text"]
            delay = int(args.get("delay_ms", 10))
            method = args.get("method", "auto")
            app_name = args.get("app_name")
            element = args.get("element")
            restore_focus = bool(args.get("restore_focus", False))

            ok = await asyncio.to_thread(
                type_text,
                text,
                delay,
                method,
                app_name,
                element,
                restore_focus,
            )
            info = f"Typed {len(text)} characters (method: {method})"
            if app_name and element:
                info += f" via AT-SPI into '{element}' in '{app_name}' (Non-disruptive)"
            if restore_focus:
                info += " [Focus Guard: focus restored]"
            return {
                "content": [{"type": "text", "text": info}],
                "isError": False,
            }

        elif name == "set_accessibility_text":
            app = args["app_name"]
            element = args["element"]
            text = args["text"]
            ok = await asyncio.to_thread(set_element_value, app, element, text)
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Set accessibility text on '{element}' in '{app}': {'Success' if ok else 'Failed'}",
                    }
                ],
                "isError": not ok,
            }

        elif name == "get_cursor_position":
            x, y = await asyncio.to_thread(get_cursor_position)
            return {
                "content": [{"type": "text", "text": json.dumps({"x": x, "y": y})}],
                "isError": False,
            }

        elif name == "get_screen_size":
            w, h = await asyncio.to_thread(get_screen_size)
            return {
                "content": [{"type": "text", "text": json.dumps({"width": w, "height": h})}],
                "isError": False,
            }

        elif name == "list_accessible_apps":
            apps = await asyncio.to_thread(list_accessible_apps)
            return {
                "content": [{"type": "text", "text": json.dumps(apps, ensure_ascii=False, indent=2)}],
                "isError": False,
            }

        elif name == "get_accessibility_tree":
            app = args.get("app_name")
            depth = int(args.get("max_depth", 4))
            nodes = int(args.get("max_nodes", 150))
            tree = await asyncio.to_thread(get_accessibility_tree, app, depth, nodes)
            return {
                "content": [{"type": "text", "text": json.dumps(tree, ensure_ascii=False, indent=2)}],
                "isError": False,
            }

        elif name == "perform_accessibility_action":
            app = args["app_name"]
            element = args["element"]
            action = args.get("action")
            ok = await asyncio.to_thread(perform_accessibility_action, app, element, action)
            return {
                "content": [{"type": "text", "text": f"Performed action on '{element}': {'Success' if ok else 'Failed'}"}],
                "isError": not ok,
            }

        elif name == "launch_isolated_app":
            command = args["command"]
            app_id = args.get("app_id")
            display = args.get("isolated_display")
            res = await asyncio.to_thread(launch_isolated_app, command, app_id, display)
            return {
                "content": [{"type": "text", "text": json.dumps(res, ensure_ascii=False, indent=2)}],
                "isError": not res.get("success", False),
            }

        elif name == "list_isolated_apps":
            active_apps = await asyncio.to_thread(list_isolated_apps)
            return {
                "content": [{"type": "text", "text": json.dumps(active_apps, ensure_ascii=False, indent=2)}],
                "isError": False,
            }

        elif name == "stop_isolated_app":
            pid = int(args["pid"])
            ok = await asyncio.to_thread(stop_isolated_app, pid)
            return {
                "content": [{"type": "text", "text": f"Stop isolated application {pid}: {'Success' if ok else 'Failed'}"}],
                "isError": not ok,
            }

        elif name == "doctor":
            rep = await asyncio.to_thread(doctor_report)
            md = format_doctor_report(rep)
            return {
                "content": [{"type": "text", "text": md}],
                "isError": False,
            }

        raise ValueError(f"Unknown tool: '{name}'")


async def run_stdio_server():
    """Run MCP server reading JSON-RPC lines from stdin and writing to stdout."""
    server = MCPServer()
    loop = asyncio.get_running_loop()
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)

    while True:
        line = await reader.readline()
        if not line:
            break

        line_str = line.decode("utf-8").strip()
        if not line_str:
            continue

        try:
            req = json.loads(line_str)
            resp = await server.handle_request(req)
            if resp is not None:
                out = json.dumps(resp, ensure_ascii=False) + "\n"
                sys.stdout.write(out)
                sys.stdout.flush()
        except Exception as e:
            err_resp = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32700,
                    "message": f"Parse error: {e}",
                },
            }
            sys.stdout.write(json.dumps(err_resp) + "\n")
            sys.stdout.flush()
