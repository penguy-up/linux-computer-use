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
SERVER_VERSION = "1.0.0"
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
        "description": "Move the mouse cursor to absolute coordinate (x, y).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "x": {"type": "integer", "description": "X coordinate."},
                "y": {"type": "integer", "description": "Y coordinate."},
            },
            "required": ["x", "y"],
        },
    },
    {
        "name": "mouse_click",
        "description": "Click the mouse at optional (x, y) coordinates. Supports left, right, middle, and multiple clicks.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "x": {"type": "integer", "description": "Optional target X coordinate."},
                "y": {"type": "integer", "description": "Optional target Y coordinate."},
                "button": {
                    "type": "string",
                    "enum": ["left", "right", "middle"],
                    "description": "Button to click (default: 'left').",
                },
                "count": {
                    "type": "integer",
                    "description": "Number of clicks: 1=single click, 2=double click, 3=triple click (default: 1).",
                },
            },
        },
    },
    {
        "name": "mouse_down",
        "description": "Press and hold mouse button.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "button": {
                    "type": "string",
                    "enum": ["left", "right", "middle"],
                    "description": "Button to press down (default: 'left').",
                },
            },
        },
    },
    {
        "name": "mouse_up",
        "description": "Release held mouse button.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "button": {
                    "type": "string",
                    "enum": ["left", "right", "middle"],
                    "description": "Button to release (default: 'left').",
                },
            },
        },
    },
    {
        "name": "release_all_buttons",
        "description": "Emergency release for any mouse buttons currently held down (prevents mouse button stuck during drag or interruption).",
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
            },
            "required": ["key_combo"],
        },
    },
    {
        "name": "type_text",
        "description": "Type literal text into the currently focused window or element.",
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
                    "enum": ["auto", "type", "clipboard"],
                    "description": "Typing method: 'auto' (default, switches to clipboard paste for Chinese/Unicode, newlines, or text > 15 chars), 'type' (keystroke emulation only), or 'clipboard' (Wayland clipboard paste via Ctrl+V).",
                },
            },
            "required": ["text"],
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
        "description": "Perform an action (e.g. click, press) directly on an accessible element.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "app_name": {"type": "string", "description": "Application name."},
                "element": {"type": "string", "description": "Element name or label."},
                "action": {"type": "string", "description": "Action name (e.g. 'click', default: primary action)."},
            },
            "required": ["app_name", "element"],
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
        msg_id = request.get("id")
        method = request.get("method")
        params = request.get("params", {})

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
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
                "id": msg_id,
                "result": {},
            }

        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "tools": TOOLS_DEFINITIONS,
                },
            }

        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            try:
                result = await self.execute_tool(tool_name, arguments)
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": result,
                }
            except Exception as e:
                err_text = f"Tool '{tool_name}' execution error: {str(e)}\n{traceback.format_exc()}"
                logger.error(err_text)
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [{"type": "text", "text": err_text}],
                        "isError": True,
                    },
                }

        else:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {
                    "code": -32601,
                    "message": f"Method '{method}' not found",
                },
            }

    async def execute_tool(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch tool calls to corresponding backend functions."""
        if name == "screenshot":
            max_w = args.get("max_width")
            max_h = args.get("max_height")
            scale = args.get("scale")
            fmt = args.get("format", "png")
            quality = args.get("quality", 80)
            crop = args.get("crop_rect")
            cursor = args.get("include_cursor", False)

            res = await asyncio.to_thread(
                capture_screenshot,
                max_width=max_w,
                max_height=max_h,
                scale=scale,
                output_format=fmt,
                quality=quality,
                crop_rect=crop,
                include_cursor=cursor,
            )
            caption = (
                f"Screenshot: {res['width']}x{res['height']} px (coordinate {res['coordinate_width']}x{res['coordinate_height']}), "
                f"scale={res['scale']}, format={res['format']}, bytes={res['bytes']}"
            )
            return {
                "content": [
                    {
                        "type": "image",
                        "data": res["base64_data"],
                        "mimeType": res["mime_type"],
                    },
                    {
                        "type": "text",
                        "text": caption,
                    },
                ],
                "isError": False,
            }

        elif name == "list_windows":
            wins = await asyncio.to_thread(list_windows)
            return {
                "content": [
                    {"type": "text", "text": json.dumps(wins, ensure_ascii=False, indent=2)},
                ],
                "isError": False,
            }

        elif name == "focus_window":
            target = args["target"]
            ok = await asyncio.to_thread(focus_window, target)
            return {
                "content": [
                    {"type": "text", "text": f"Focus window '{target}': {'Success' if ok else 'Failed'}"},
                ],
                "isError": not ok,
            }

        elif name == "close_window":
            target = args["target"]
            ok = await asyncio.to_thread(close_window, target)
            return {
                "content": [
                    {"type": "text", "text": f"Close window '{target}': {'Success' if ok else 'Failed'}"},
                ],
                "isError": not ok,
            }

        elif name == "maximize_window":
            target = args["target"]
            ok = await asyncio.to_thread(maximize_window, target)
            return {
                "content": [
                    {"type": "text", "text": f"Maximize window '{target}': {'Success' if ok else 'Failed'}"},
                ],
                "isError": not ok,
            }

        elif name == "minimize_window":
            target = args["target"]
            ok = await asyncio.to_thread(minimize_window, target)
            return {
                "content": [
                    {"type": "text", "text": f"Minimize window '{target}': {'Success' if ok else 'Failed'}"},
                ],
                "isError": not ok,
            }

        elif name == "mouse_move":
            x = int(args["x"])
            y = int(args["y"])
            ok = await asyncio.to_thread(mouse_move, x, y)
            return {
                "content": [{"type": "text", "text": f"Mouse moved to ({x}, {y})"}],
                "isError": False,
            }

        elif name == "mouse_click":
            x = args.get("x")
            y = args.get("y")
            btn = args.get("button", "left")
            cnt = int(args.get("count", 1))
            ok = await asyncio.to_thread(mouse_click, x, y, btn, cnt)
            pos_text = f" at ({x}, {y})" if (x is not None and y is not None) else ""
            return {
                "content": [{"type": "text", "text": f"Clicked {btn} button {cnt} time(s){pos_text}"}],
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
            await asyncio.to_thread(mouse_drag, sx, sy, ex, ey, btn)
            return {
                "content": [{"type": "text", "text": f"Dragged from ({sx}, {sy}) to ({ex}, {ey})"}],
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
            ok = await asyncio.to_thread(press_key, combo)
            return {
                "content": [{"type": "text", "text": f"Pressed key '{combo}'"}],
                "isError": False,
            }

        elif name == "type_text":
            text = args["text"]
            delay = int(args.get("delay_ms", 10))
            method = args.get("method", "auto")
            ok = await asyncio.to_thread(type_text, text, delay, method)
            return {
                "content": [{"type": "text", "text": f"Typed {len(text)} characters (method: {method})"}],
                "isError": False,
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
