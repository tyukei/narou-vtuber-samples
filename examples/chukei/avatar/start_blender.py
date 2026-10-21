"""Start a separate interactive Blender instance with MCP and the VRM add-on.

Pass addon directories through AVATAR_VRM_ADDON and AVATAR_MCP_ADDON.
"""
import os
import sys
from pathlib import Path
import bpy

vrm = Path(os.environ["AVATAR_VRM_ADDON"])
sys.path.insert(0, str(vrm.parent))
sys.path.insert(0, os.environ["AVATAR_MCP_ADDON"])
bpy.ops.preferences.addon_enable(module=vrm.name)
bpy.ops.preferences.addon_enable(module="blender_mcp")
import blender_mcp
bpy.context.scene.blendermcp_port = 9877
bpy.context.scene.blendermcp_auto_start_server = False
server = blender_mcp.BlenderMCPServer(port=9877)
bpy.types.blendermcp_server = server
server.start()
bpy.context.scene.blendermcp_server_running = True
print("AVATAR_MCP_READY", bpy.app.version_string, flush=True)
