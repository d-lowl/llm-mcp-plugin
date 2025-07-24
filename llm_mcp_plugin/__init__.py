"""LLM Plugin for Model Context Protocol (MCP) servers.

This package provides a plugin for the LLM command-line tool that enables
using MCP servers as toolboxes in conversations.
"""

from .mcp_toolbox import MCPToolbox
from .mcp_client import MCPClient
from .config import MCPServerConfig

__version__ = "0.1.0"
__all__ = ["MCPToolbox", "MCPClient", "MCPServerConfig"] 