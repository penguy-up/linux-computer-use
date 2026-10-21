"""Test non-disruptive Computer Use features (CursorGuard, FocusGuard, AT-SPI, Isolation)."""

from __future__ import annotations

import asyncio
import json
import pytest
from deepin_computer_use.input.pointer import CursorGuard, get_cursor_position, mouse_click, mouse_move
from deepin_computer_use.windowing.treeland import FocusGuard
from deepin_computer_use.isolation import launch_isolated_app, list_isolated_apps, stop_isolated_app
from deepin_computer_use.server import MCPServer


def test_cursor_guard():
    # Set known position
    mouse_move(100, 200)
    orig_x, orig_y = get_cursor_position()

    with CursorGuard(enabled=True):
        # Move elsewhere
        mouse_move(800, 900)
        curr_x, curr_y = get_cursor_position()
        assert curr_x == 800 and curr_y == 900

    # Cursor should have restored to original position
    restored_x, restored_y = get_cursor_position()
    assert restored_x == orig_x and restored_y == orig_y


def test_mouse_click_restore_cursor():
    mouse_move(150, 250)
    orig_x, orig_y = get_cursor_position()

    # Click with restore_cursor=True at target (600, 700)
    mouse_click(600, 700, button="left", restore_cursor=True)

    # After click, cursor should be back to 150, 250
    post_x, post_y = get_cursor_position()
    assert post_x == orig_x and post_y == orig_y


def test_focus_guard():
    guard = FocusGuard(enabled=True)
    with guard:
        pass
    # FocusGuard initialized and exited cleanly without error


def test_isolated_app_lifecycle():
    # Launch a simple sleeping subprocess
    res = launch_isolated_app("sleep 10", app_id="test-sleep")
    assert res["success"] is True
    pid = res["pid"]
    assert pid > 0

    # Check that it appears in active list
    active = list_isolated_apps()
    pids = [app["pid"] for app in active]
    assert pid in pids

    # Stop the app
    stopped = stop_isolated_app(pid)
    assert stopped is True


def test_mcp_new_tools_listed():
    server = MCPServer()
    req = {
        "jsonrpc": "2.0",
        "id": 10,
        "method": "tools/list",
        "params": {},
    }
    resp = asyncio.run(server.handle_request(req))
    assert resp is not None
    tools = resp["result"]["tools"]
    tool_names = [t["name"] for t in tools]

    assert "set_accessibility_text" in tool_names
    assert "get_active_window" in tool_names
    assert "launch_isolated_app" in tool_names
    assert "list_isolated_apps" in tool_names
    assert "stop_isolated_app" in tool_names


def test_mcp_get_active_window_call():
    server = MCPServer()
    req = {
        "jsonrpc": "2.0",
        "id": 11,
        "method": "tools/call",
        "params": {
            "name": "get_active_window",
            "arguments": {},
        },
    }
    resp = asyncio.run(server.handle_request(req))
    assert resp is not None
    assert not resp["result"]["isError"]
    data = json.loads(resp["result"]["content"][0]["text"])
    assert "active_app" in data
    assert "active_window" in data


def test_mcp_isolated_app_tools():
    server = MCPServer()
    # 1. Launch
    launch_req = {
        "jsonrpc": "2.0",
        "id": 12,
        "method": "tools/call",
        "params": {
            "name": "launch_isolated_app",
            "arguments": {"command": "sleep 10", "app_id": "test-mcp-sleep"},
        },
    }
    resp = asyncio.run(server.handle_request(launch_req))
    assert resp is not None
    assert not resp["result"]["isError"]
    res_data = json.loads(resp["result"]["content"][0]["text"])
    pid = res_data["pid"]

    # 2. List
    list_req = {
        "jsonrpc": "2.0",
        "id": 13,
        "method": "tools/call",
        "params": {
            "name": "list_isolated_apps",
            "arguments": {},
        },
    }
    list_resp = asyncio.run(server.handle_request(list_req))
    assert list_resp is not None
    assert str(pid) in list_resp["result"]["content"][0]["text"]

    # 3. Stop
    stop_req = {
        "jsonrpc": "2.0",
        "id": 14,
        "method": "tools/call",
        "params": {
            "name": "stop_isolated_app",
            "arguments": {"pid": pid},
        },
    }
    stop_resp = asyncio.run(server.handle_request(stop_req))
    assert stop_resp is not None
    assert not stop_resp["result"]["isError"]
