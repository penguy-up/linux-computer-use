"""CLI entry point for deepin_computer_use."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from .diagnostics import doctor_report, format_doctor_report
from .screenshot import capture_screenshot
from .server import run_stdio_server
from .windowing import list_windows


def main():
    parser = argparse.ArgumentParser(
        description="Deepin OS V25 (Treeland Wayland) Computer Use MCP Server and CLI tool"
    )
    parser.add_argument(
        "--doctor",
        action="store_true",
        help="Run system integration health check and diagnostics.",
    )
    parser.add_argument(
        "--list-windows",
        action="store_true",
        help="List running Wayland toplevel windows.",
    )
    parser.add_argument(
        "--screenshot",
        metavar="OUTPUT_FILE",
        help="Capture desktop screenshot and save to specified file.",
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Run MCP JSON-RPC stdio server (default behavior).",
    )

    args = parser.parse_args()

    if args.doctor:
        report = doctor_report()
        print(format_doctor_report(report))
        sys.exit(0 if report["status"] != "UNHEALTHY" else 1)

    if args.list_windows:
        wins = list_windows()
        print(json.dumps(wins, ensure_ascii=False, indent=2))
        sys.exit(0)

    if args.screenshot:
        import base64
        res = capture_screenshot(output_format="png")
        data = base64.b64decode(res["base64_data"])
        with open(args.screenshot, "wb") as f:
            f.write(data)
        print(f"Screenshot saved to {args.screenshot} ({res['width']}x{res['height']} px, {res['bytes']} bytes)")
        sys.exit(0)

    # Default: run stdio MCP server
    try:
        asyncio.run(run_stdio_server())
    except (KeyboardInterrupt, BrokenPipeError):
        pass


if __name__ == "__main__":
    main()
