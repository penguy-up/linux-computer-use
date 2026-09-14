#!/usr/bin/env bash
set -e

# Resolve script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Ensure WAYLAND_DISPLAY is set
export WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-treeland.socket}"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
export DISPLAY="${DISPLAY:-:1}"

# Prepend project's bin/ directory to PATH so bundled grim, wlrctl, wtype are found
export PATH="$PROJECT_ROOT/bin:$PATH"

# Run MCP server
exec python3 -m deepin_computer_use "$@"
