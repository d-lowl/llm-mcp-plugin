"""LLM Plugin for Model Context Protocol (MCP) servers.

This package provides a plugin for the LLM command-line tool that enables
using MCP servers as toolboxes in conversations.
"""

from .config import MCPServerConfig
from .mcp_client import MCPClient
from .mcp_toolbox import MCPToolbox

__version__ = "0.1.0"
__all__ = ["MCPToolbox", "MCPClient", "MCPServerConfig"]
