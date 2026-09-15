#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to automate WeChat and mini-program operations via deepin-computer-use MCP server.
"""

import os
import sys
import json
import time
import base64
import subprocess
from typing import Any, Dict, Optional

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_SCRIPT = os.path.join(SCRIPT_DIR, "run_server.sh")
ENV = {
    **os.environ,
    "WAYLAND_DISPLAY": "treeland.socket",
    "DISPLAY": ":1"
}

class MCPClient:
    def __init__(self, command: str, env: Dict[str, str]):
        self.proc = subprocess.Popen(
            [command],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env
        )
        self.req_id = 0

    def send_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        self.req_id += 1
        req = {
            "jsonrpc": "2.0",
            "id": self.req_id,
            "method": method,
            "params": params
        }
        self.proc.stdin.write(json.dumps(req) + "\n")
        self.proc.stdin.flush()

        line = self.proc.stdout.readline()
        if not line:
            err = self.proc.stderr.read()
            raise RuntimeError(f"MCP server closed unexpectedly: {err}")
        return json.loads(line)

    def initialize(self) -> Dict[str, Any]:
        return self.send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "wechat-test-client", "version": "1.0.0"}
        })

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        resp = self.send_request("tools/call", {
            "name": name,
            "arguments": arguments
        })
        if "error" in resp:
            raise RuntimeError(f"Tool {name} error: {resp['error']}")
        return resp.get("result", {})

    def close(self):
        try:
            self.proc.terminate()
            self.proc.wait(timeout=2)
        except Exception:
            self.proc.kill()

def main():
    print("==================================================")
    print("🚀 连接 deepin-computer-use MCP 服务...")
    print("==================================================")
    client = MCPClient(SERVER_SCRIPT, ENV)

    # 1. Initialize
    init_res = client.initialize()
    print("✅ MCP 初始化成功:", init_res.get("result", {}).get("serverInfo"))

    # 2. Doctor Check
    print("\n--- 1. 系统健康度诊断 (doctor) ---")
    doc_res = client.call_tool("doctor", {})
    for c in doc_res.get("content", []):
        if c.get("type") == "text":
            print(c.get("text"))

    # 3. List Windows
    print("\n--- 2. 列出桌面活动窗口 (list_windows) ---")
    win_res = client.call_tool("list_windows", {})
    for c in win_res.get("content", []):
        if c.get("type") == "text":
            windows = json.loads(c.get("text"))
            print(f"检测到 {len(windows)} 个活动顶层窗口:")
            for w in windows:
                print(f"  [{w.get('backend')}] id={w.get('id')} app_id='{w.get('app_id')}' title='{w.get('title')}'")

    # 4. Focus WeChat Window
    print("\n--- 3. 聚焦微信窗口 (focus_window) ---")
    foc_res = client.call_tool("focus_window", {"target": "wechat"})
    for c in foc_res.get("content", []):
        print(" ", c.get("text"))

    time.sleep(0.5)

    # 5. Take Screenshot
    print("\n--- 4. 获取当前桌面截屏 (screenshot) ---")
    shot_res = client.call_tool("screenshot", {"include_cursor": True})
    img_data = None
    for c in shot_res.get("content", []):
        if c.get("type") == "text":
            print("  截屏元数据:", c.get("text"))
        elif c.get("type") == "image":
            img_data = base64.b64decode(c.get("data"))
            out_file = "/tmp/mcp_wechat_screen.png"
            with open(out_file, "wb") as f:
                f.write(img_data)
            print(f"  截屏保存至: {out_file} (体积: {len(img_data)} 字节)")

    # 6. AT-SPI Inspection
    print("\n--- 5. 检查 AT-SPI 语义树 (get_accessibility_tree) ---")
    atspi_res = client.call_tool("get_accessibility_tree", {
        "app_name": "wechat",
        "max_depth": 5,
        "max_nodes": 60
    })
    for c in atspi_res.get("content", []):
        if c.get("type") == "text":
            tree_data = json.loads(c.get("text"))
            print(f"  微信无障碍控件数: {tree_data.get('nodes_extracted')}")

    # 7. Check if Mini-Program is active
    print("\n--- 6. 检查小程序窗口状态 ---")
    has_mp = any("WeChatAppEx" in w.get("app_id", "") or "创座" in w.get("title", "") for w in windows)
    if has_mp:
        print("  🎉 检测到小程序窗口已存在，尝试激活小程序窗口...")
        client.call_tool("focus_window", {"target": "创座"})
    else:
        print("  当前尚未打开小程序。微信当前状态为就绪/登录界面。")

    print("\n==================================================")
    print("🏁 MCP 服务功能验证全部通过！")
    print("==================================================")
    client.close()

if __name__ == "__main__":
    main()
