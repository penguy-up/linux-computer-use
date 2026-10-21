# Deepin Computer Use MCP 服务

[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Deepin](https://img.shields.io/badge/Deepin%20OS-V25.2%20Wayland-0078d7.svg)](https://www.deepin.org/)
[![Compositor](https://img.shields.io/badge/Compositor-Treeland%20(wlroots)-success.svg)](https://github.com/linuxdeepin/treeland)
[![Version](https://img.shields.io/badge/version-v1.1.0-green.svg)](pyproject.toml)

[English](README.md) | 简体中文

专门针对 **Deepin OS V25.2** 及其 **Treeland** Wayland 合成器深度定制的 [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) **Computer Use（计算机交互操作）** 服务。

本项目借鉴了 [ilysenko/codex-desktop-linux](https://github.com/ilysenko/codex-desktop-linux) 的整体架构理念，与 [linuxdeepin/treeland](https://github.com/linuxdeepin/treeland) 的 Wayland 原生协议完成深度集成，并针对 Agent 自动化交互中**“不与用户争抢物理鼠标与键盘焦点”**的核心需求提供了完整的原生防抢占与语义直达方案。

---

## 核心特性

- **⚡ Wayland 原生高效截图**：利用 Treeland 导出的 `zwlr_screencopy_manager_v1`（通过内置 `grim`），实现毫秒级零延迟截屏，无系统弹窗打扰；支持等比缩放、区域裁切、JPEG/PNG 格式压缩及体积控制。
- **🪟 Treeland 顶层窗口管理**：集成 `zwlr_foreign_toplevel_manager_v1` 协议（通过内置 `wlrctl`），能够枚举、激活聚焦、关闭、最大化/最小化当前桌面运行的 Wayland 与 XWayland 窗口。
- **🛡️ 零抢占 / 不扰民模式 (Non-Disruptive Mode)**：
  - **AT-SPI 纯语义输入与点击**：通过 `set_accessibility_text` 与 `perform_accessibility_action`，直接经由 D-Bus 接口在后台向目标控件写入文本或触发动作，**完全不移动物理鼠标，不抢夺键盘焦点**。
  - **光标保护机制 (Cursor Guard)**：物理点击与拖拽支持 `restore_cursor` 参数，在毫秒级瞬态动作完成后瞬间将物理鼠标指针复原回原坐标，绝不打乱用户当前鼠标轨迹。
  - **焦点保护机制 (Focus Guard)**：击键与文本输入支持 `restore_focus` 参数，操作完成后自动将桌面焦点切回用户原本正在输入的窗口。
  - **独立沙箱会话 (Isolated Session)**：提供 `launch_isolated_app`、`list_isolated_apps`、`stop_isolated_app`，支持为后台任务提供隔离的运行环境，彻底与当前桌面绝缘。
- **⌨️ Wayland 虚拟键盘**：基于 `zwp_virtual_keyboard_manager_v1` 协议（通过内置 `wtype` 与 `wlrctl`），无需 root 权限即可直接输入文字、触发各类复杂组合快捷键（如 `Ctrl+C`、`Super`、`Alt+Tab` 等）。
- **🖱️ 高精度鼠标与指针控制**：支持基于 `/dev/uinput` 的绝对坐标指针设备，将逻辑桌面像素精确映射到屏幕，并具备 `ydotool` 与 XWayland `xdotool` 回退机制。
- **♿ AT-SPI 无障碍组件树提取**：集成 Linux AT-SPI 2.0，可遍历当前系统及目标应用的 UI 控件树、获取控件边界坐标、获取当前前台激活窗口（`get_active_window`）。
- **🩺 自带 Doctor 系统诊断**：提供 CLI 和 MCP 工具级别的自检报告，覆盖操作系统、Treeland 合成器、Wayland 协议可用性、权限状态和辅助功能总线。
- **📦 内置免安装独立辅助工具**：在 `bin/` 目录下内置了经过系统适配验证的 `grim`、`wlrctl`、`wtype` 独立工具，开箱即用，无需额外使用 `sudo apt` 安装依赖。

---

## 支持的 MCP Tools

| 工具名称 | 描述 |
| :--- | :--- |
| `screenshot` | 截取屏幕画面，支持缩放、格式（png/jpeg）、压缩质量、矩形裁切与光标显示。 |
| `list_windows` | 列出当前桌面所有活动的 Wayland 与 XWayland 顶层窗口（含 app_id 与标题）。 |
| `get_active_window` | 获取当前正在前台聚焦/激活的应用名称与窗口标题。 |
| `focus_window` | 通过 `app_id` 或标题关键词聚焦并激活目标窗口。 |
| `close_window` | 通过 `app_id` 或标题关闭指定窗口。 |
| `maximize_window` | 最大化指定窗口。 |
| `minimize_window` | 最小化指定窗口。 |
| `mouse_move` | 移动光标至绝对逻辑坐标 `(x, y)`。 |
| `mouse_click` | 在指定坐标点击鼠标（支持左键/右键/中键，支持 `restore_cursor` 光标自动复位防抢占）。 |
| `mouse_down` / `mouse_up` | 按下与释放鼠标按键。 |
| `mouse_drag` | 从起始坐标平滑拖拽至结束坐标（支持 `restore_cursor` 光标自动复位）。 |
| `mouse_scroll` | 滚动鼠标滚轮（垂直方向或水平方向）。 |
| `press_key` | 发送单个按键或组合快捷键（支持 `restore_focus` 自动恢复用户焦点）。 |
| `type_text` | 向输入框输入文本（支持直接传入 `app_name` 与 `element` 走 AT-SPI 语义输入，或设置 `restore_focus` 恢复焦点）。 |
| `set_accessibility_text` | **【零扰民】** 直接通过 AT-SPI 向控件注入文本，**不移动光标、不切走焦点**。 |
| `perform_accessibility_action` | **【零扰民】** 直接通过 AT-SPI 触发控件语义动作（点击、展开等），**无需鼠标光标参与**。 |
| `get_cursor_position` | 获取当前鼠标光标所在坐标。 |
| `get_screen_size` | 获取屏幕分辨率与逻辑尺寸。 |
| `list_accessible_apps` | 列出在 AT-SPI 辅助功能总线上注册的所有应用程序。 |
| `get_accessibility_tree` | 提取全局或指定应用的 UI 控件层次结构与边界框。 |
| `launch_isolated_app` | 在独立隔离环境中拉起后台应用，不与用户桌面产生交互冲突。 |
| `list_isolated_apps` | 列出所有正在运行的隔离应用实例。 |
| `stop_isolated_app` | 终止指定的隔离应用。 |
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
pytest -v
```

---

## 开源协议

本项目采用 [Apache-2.0 License](LICENSE) 协议开源。
