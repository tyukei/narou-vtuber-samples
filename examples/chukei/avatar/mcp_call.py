"""Run one Blender MCP tool and retain its real response (uv run --with mcp)."""
import asyncio
import base64
import json
import os
import sys
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    tool, argument_file, output = sys.argv[1:]
    server = os.environ.get("AVATAR_MCP_SERVER")
    env = dict(os.environ)
    env["BLENDER_MCP_DISABLE_TELEMETRY"] = "1"
    params = StdioServerParameters(command=server or "uvx", args=[] if server else ["mcp-for-blender==2.1.3"], env=env)
    async with stdio_client(params) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()
            args = json.loads(Path(argument_file).read_text())
            result = await session.call_tool(tool, args)
            records = []
            for item in result.content:
                if item.type == "image":
                    path = Path(output).with_suffix(".png")
                    path.write_bytes(base64.b64decode(item.data))
                    records.append({"image": str(path)})
                elif item.type == "text":
                    records.append({"text": item.text})
            Path(output).write_text(json.dumps({"isError": result.isError, "content": records}, ensure_ascii=False, indent=2))
            print(Path(output).read_text())

asyncio.run(main())
