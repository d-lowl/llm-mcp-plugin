#!/usr/bin/env python3
"""
Main entry point for llm-mcp-plugin demonstration.

This script shows how to use the plugin programmatically and provides
a command-line interface for testing MCP server integrations.
"""

import asyncio
import sys
from pathlib import Path

# Add the package to path for development
sys.path.insert(0, str(Path(__file__).parent))

import llm

from llm_mcp_plugin import MCPServerConfig
from llm_mcp_plugin.plugin import get_config


async def demo_filesystem_mcp() -> None:
    """Demonstrate using a filesystem MCP server."""
    print("🗂️  Setting up filesystem MCP server...")

    # Configure a filesystem MCP server (you'll need the MCP server installed)
    fs_config = MCPServerConfig(
        name="filesystem",
        transport="stdio",
        command="python",
        args=["-m", "mcp.server.filesystem", str(Path.home())],
        description="File system operations",
        timeout=30,
        url=None,
        stderr_mode="disable",
        stderr_file=None,
        stderr_append=False,
    )

    # Add to configuration
    config = get_config()
    config.add_server(fs_config)

    try:
        # Get the toolbox
        fs_toolbox = llm.get_mcp_toolbox("filesystem")  # type: ignore[attr-defined]

        # Initialize and show capabilities
        await fs_toolbox._ensure_initialized()
        capabilities = await fs_toolbox.list_capabilities()

        print("✅ Connected to filesystem MCP server!")
        print(f"   Tools: {len(capabilities['tools'])}")
        print(f"   Resources: {len(capabilities['resources'])}")
        print(f"   Available tools: {capabilities['tools']}")

        # Demo with an LLM (if you have one configured)
        try:
            model = llm.get_model("gpt-4o-mini")
            conversation = model.conversation(tools=[fs_toolbox])

            print("\n🤖 Testing with LLM...")
            response = conversation.chain("List the files in my home directory")
            print(f"Response: {response.text()}")

        except Exception as e:
            print(f"⚠️  LLM demo skipped (no model configured): {e}")

    except Exception as e:
        print(f"❌ Failed to set up filesystem MCP: {e}")
        print("   Make sure you have the MCP Python SDK installed:")
        print("   pip install mcp")


async def list_configured_servers() -> None:
    """List all configured MCP servers."""
    servers = llm.list_mcp_servers()  # type: ignore[attr-defined]

    if not servers:
        print("📝 No MCP servers configured yet.")
        return

    print(f"📋 Configured MCP servers ({len(servers)}):")
    config = get_config()

    for name in servers:
        server_config = config.get_server(name)
        if server_config:
            print(f"   • {name}: {server_config.transport}")
            if server_config.description:
                print(f"     {server_config.description}")

            # Test connection
            try:
                toolbox = llm.get_mcp_toolbox(name)  # type: ignore[attr-defined]
                await toolbox._ensure_initialized()
                capabilities = await toolbox.list_capabilities()
                print(f"     ✅ Connected ({len(capabilities['tools'])} tools)")
            except Exception as e:
                print(f"     ❌ Connection failed: {e}")


def show_usage() -> None:
    """Show usage information."""
    print(
        """
🔧 LLM MCP Plugin Demo

This plugin allows you to use Model Context Protocol (MCP) servers
as toolboxes in LLM conversations.

Commands:
  python main.py demo      - Run filesystem MCP demo
  python main.py list      - List configured servers
  python main.py cli       - Show CLI usage examples

Python Usage:
  import llm
  toolbox = llm.get_mcp_toolbox("server_name")
  model = llm.get_model("gpt-4")
  conversation = model.conversation(tools=[toolbox])
  response = conversation.chain("Your prompt here")

CLI Usage (after installation):
  llm mcp add myserver --transport stdio --command python --args server.py
  llm mcp list
  llm mcp test myserver
  llm mcp info myserver
    """
    )


def show_cli_examples() -> None:
    """Show CLI usage examples."""
    print(
        """
📚 LLM MCP Plugin CLI Examples

# Add a Toggl Track MCP server
llm mcp add toggl \\
  --transport stdio \\
  --command node \\
  --args /path/to/toggl-track-mcp/dist/index.js \\
  --env TOGGL_API_TOKEN=your_token \\
  --description "Time tracking integration"

# Add a filesystem MCP server
llm mcp add filesystem \\
  --transport stdio \\
  --command python \\
  --args -m \\
  --args mcp.server.filesystem \\
  --args /path/to/allowed/dir \\
  --description "File operations"

# Add an HTTP MCP server
llm mcp add weather \\
  --transport http \\
  --url http://localhost:8000/mcp \\
  --header "Authorization: Bearer token" \\
  --description "Weather API"

# List all servers
llm mcp list

# Test a server connection
llm mcp test toggl

# Get detailed server info
llm mcp info toggl

# Remove a server
llm mcp remove toggl
    """
    )


async def main() -> None:
    """Main entry point."""
    if len(sys.argv) < 2:
        show_usage()
        return

    command = sys.argv[1].lower()

    if command == "demo":
        await demo_filesystem_mcp()
    elif command == "list":
        await list_configured_servers()
    elif command == "cli":
        show_cli_examples()
    else:
        print(f"Unknown command: {command}")
        show_usage()


if __name__ == "__main__":
    print("🚀 LLM MCP Plugin")
    asyncio.run(main())
