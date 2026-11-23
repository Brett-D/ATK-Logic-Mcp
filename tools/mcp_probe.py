"""Call the atk-dl16 MCP server's tools from a shell, over stdio.

Usage:
    python tools/mcp_probe.py                          # list the tools
    python tools/mcp_probe.py logic_status
    python tools/mcp_probe.py logic_capture @args.json # arguments from a JSON file
    python tools/mcp_probe.py logic_capture '{"channels": [0, 8], "pwm0_hz": 100000}'

The server runs as `<python> run_mcp_server.py` from this checkout with the current environment,
so ATK_DL16_CLI and ATK_DL16_DATA_DIR pass through. Use --python to run it with another
interpreter, for example the venv your MCP client uses.
"""
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER = Path(__file__).resolve().parents[1] / "run_mcp_server.py"


async def probe(params: StdioServerParameters, tool: Optional[str], arguments: dict) -> None:
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            if not tool:
                for t in (await session.list_tools()).tools:
                    summary = (t.description or "").strip().splitlines()
                    print(t.name, "-", summary[0] if summary else "")
                return
            result = await session.call_tool(tool, arguments)
            for item in result.content:
                print(getattr(item, "text", item))


def main() -> None:
    ap = argparse.ArgumentParser(description="Call the atk-dl16 MCP server's tools over stdio.")
    ap.add_argument("tool", nargs="?", help="tool to call (omit to list the tools)")
    ap.add_argument("arguments", nargs="?", default="{}",
                    help="tool arguments as a JSON object, or @file.json to read them from a file")
    ap.add_argument("--python", default=sys.executable, help="interpreter that runs the server")
    ap.add_argument("--server", type=Path, default=SERVER, help="server script (default: run_mcp_server.py)")
    args = ap.parse_args()

    text = args.arguments
    if text.startswith("@"):
        text = Path(text[1:]).read_text(encoding="utf-8")
    params = StdioServerParameters(command=args.python, args=[str(args.server)], env=dict(os.environ))
    asyncio.run(probe(params, args.tool, json.loads(text)))


if __name__ == "__main__":
    main()
