# Deepin Computer Use MCP 服务

[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Deepin](https://img.shields.io/badge/Deepin%20OS-V25.2%20Wayland-0078d7.svg)](https://www.deepin.org/)
[![Compositor](https://img.shields.io/badge/Compositor-Treeland%20(wlroots)-success.svg)](https://github.com/linuxdeepin/treeland)

[English](README.md) | 简体中文

专门针对 **Deepin OS V25.2** 及其 **Treeland** Wayland 合成器深度定制的 [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) **Computer Use（计算机交互操作）** 服务。

本项目借鉴了 [ilysenko/codex-desktop-linux](https://github.com/ilysenko/codex-desktop-linux) 的整体架构理念，并与 [linuxdeepin/treeland](https://github.com/linuxdeepin/treeland) 的 Wayland 原生协议完成深度集成。

---

## 核心特性

- **⚡ Wayland 原生高效截图**：利用 Treeland 导出的 `zwlr_screencopy_manager_v1`（通过内置 `grim`），实现毫秒级零延迟截屏，无系统弹窗打扰；支持等比缩放、区域裁切、JPEG/PNG 格式压缩及体积控制。
- **🪟 Treeland 顶层窗口管理**：集成 `zwlr_foreign_toplevel_manager_v1` 协议（通过内置 `wlrctl`），能够枚举、激活聚焦、关闭、最大化/最小化当前桌面运行的 Wayland 与 XWayland 窗口。
- **⌨️ Wayland 虚拟键盘**：基于 `zwp_virtual_keyboard_manager_v1` 协议（通过内置 `wtype` 与 `wlrctl`），无需 root 权限即可直接输入文字、触发各类复杂组合快捷键（如 `Ctrl+C`、`Super`、`Alt+Tab` 等）。
- **🖱️ 高精度鼠标与指针控制**：支持基于 `/dev/uinput` 的绝对坐标指针设备，将逻辑桌面像素精确映射到屏幕，并具备 `ydotool` 与 XWayland `xdotool` 回退机制。
- **♿ AT-SPI 无障碍组件树提取**：集成 Linux AT-SPI 2.0，可遍历当前系统及目标应用的 UI 控件树、获取控件边界坐标，并能直接触发控件的语义动作（如点击按钮、切换选框、输入文字）。
- **🩺 自带 Doctor 系统诊断**：提供 CLI 和 MCP 工具级别的自检报告，覆盖操作系统、Treeland 合成器、Wayland 协议可用性、权限状态和辅助功能总线。
- **📦 内置免安装独立辅助工具**：在 `bin/` 目录下内置了经过系统适配验证的 `grim`、`wlrctl`、`wtype` 独立工具，开箱即用，无需额外使用 `sudo apt` 安装依赖。

---

## 支持的 MCP Tools

| 工具名称 | 描述 |
| :--- | :--- |
| `screenshot` | 截取屏幕画面，支持缩放、格式（png/jpeg）、压缩质量、矩形裁切与光标显示。 |
| `list_windows` | 列出当前桌面所有活动的 Wayland 与 XWayland 顶层窗口（含 app_id 与标题）。 |
| `focus_window` | 通过 `app_id` 或标题关键词聚焦并激活目标窗口。 |
| `close_window` | 通过 `app_id` 或标题关闭指定窗口。 |
| `maximize_window` | 最大化指定窗口。 |
| `minimize_window` | 最小化指定窗口。 |
| `mouse_move` | 移动光标至绝对逻辑坐标 `(x, y)`。 |
| `mouse_click` | 在指定坐标点击鼠标（支持左键、右键、中键，以及单/双/三击）。 |
| `mouse_down` / `mouse_up` | 按下与释放鼠标按键。 |
| `mouse_drag` | 从起始坐标平滑拖拽至结束坐标。 |
| `mouse_scroll` | 滚动鼠标滚轮（垂直方向或水平方向）。 |
| `press_key` | 发送单个按键或组合快捷键（如 `Ctrl+Shift+T`、`Super`、`Return`、`Escape` 等）。 |
| `type_text` | 向当前聚焦的输入框输入文本字符。 |
| `get_cursor_position` | 获取当前鼠标光标所在坐标。 |
| `get_screen_size` | 获取屏幕分辨率与逻辑尺寸。 |
| `list_accessible_apps` | 列出在 AT-SPI 辅助功能总线上注册的所有应用程序。 |
| `get_accessibility_tree` | 提取全局或指定应用的 UI 控件层次结构与边界框。 |
| `perform_accessibility_action` | 对特定可访问性控件执行语义动作（如点击、展开等）。 |
| `doctor` | 输出系统与 Treeland 环境的健康度诊断报告。 |

---

## 快速上手

### 1. 运行环境体检 (Doctor)

```bash
python3 -m deepin_computer_use --doctor
```

### 2. 截取一张测试图片

```bash
python3 -m deepin_computer_use --screenshot test.png
```

### 3. 在 MCP 客户端中配置

编辑您的 Claude Desktop (`claude_desktop_config.json`) 或 Antigravity / Codex 的 MCP 配置文件：

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

## 硬件鼠标指针权限（可选）

键盘输入、窗口控制、截屏捕获和 AT-SPI 辅助功能树提取**完全无需任何 root 权限**即可直接工作。

如果您需要启用内核级 `/dev/uinput` 绝对坐标模拟指针（直接向内核输入子系统注入硬件鼠标事件），只需运行一次权限配置脚本：

```bash
./scripts/setup_permissions.sh
```

---

## 运行单元测试

```bash
pytest -v tests/
```

---

## 开源协议

本项目采用 [Apache-2.0 License](LICENSE) 协议开源。
