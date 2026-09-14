"""Test standard MCP JSON-RPC protocol handling."""

from __future__ import annotations

import asyncio
import pytest
from deepin_computer_use.server import MCPServer


def test_initialize_handshake():
    server = MCPServer()
    init_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0.0"},
        },
    }
    resp = asyncio.run(server.handle_request(init_request))
    assert resp is not None
    assert resp["id"] == 1
    assert "result" in resp
    assert resp["result"]["serverInfo"]["name"] == "deepin-computer-use"
    assert "tools" in resp["result"]["capabilities"]


def test_tools_list():
    server = MCPServer()
    req = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {},
    }
    resp = asyncio.run(server.handle_request(req))
    assert resp is not None
    tools = resp["result"]["tools"]
    tool_names = [t["name"] for t in tools]
    assert "screenshot" in tool_names
    assert "list_windows" in tool_names
    assert "focus_window" in tool_names
    assert "press_key" in tool_names
    assert "type_text" in tool_names
    assert "mouse_click" in tool_names
    assert "doctor" in tool_names


def test_doctor_call():
    server = MCPServer()
    req = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "doctor",
            "arguments": {},
        },
    }
    resp = asyncio.run(server.handle_request(req))
    assert resp is not None
    assert not resp["result"]["isError"]
    content = resp["result"]["content"][0]["text"]
    assert "Deepin Computer Use Diagnostics" in content
