"""LLM plugin for MCP server integration."""

import asyncio
import logging
from typing import Dict, List, Optional

import click
import llm

from .config import MCPPluginConfig, MCPServerConfig
from .mcp_toolbox import MCPToolbox

logger = logging.getLogger(__name__)

# Global registry of MCP toolboxes
_mcp_toolboxes: Dict[str, MCPToolbox] = {}
_config: Optional[MCPPluginConfig] = None


def get_config() -> MCPPluginConfig:
    """Get the global MCP plugin configuration."""
    global _config
    if _config is None:
        _config = MCPPluginConfig.load_from_file()
    return _config


def get_mcp_toolbox(name: str) -> MCPToolbox:
    """Get an MCP toolbox by name."""
    global _mcp_toolboxes

    if name not in _mcp_toolboxes:
        config = get_config()
        server_config = config.get_server(name)
        if not server_config:
            raise ValueError(f"MCP server '{name}' not found")

        _mcp_toolboxes[name] = MCPToolbox(server_config)

    return _mcp_toolboxes[name]


def list_mcp_servers() -> List[str]:
    """List all configured MCP server names."""
    config = get_config()
    return list(config.servers.keys())


def clear_mcp_cache() -> None:
    """Clear the MCP toolbox cache."""
    global _mcp_toolboxes
    # Close any persistent sessions before clearing
    try:
        async def _close_all() -> None:
            for toolbox in list(_mcp_toolboxes.values()):
                try:
                    if getattr(toolbox.config, "persistent", False):
                        await toolbox.client.aclose()
                except Exception:
                    pass

        asyncio.run(_close_all())
    except RuntimeError:
        # If there's already a running loop (unlikely in CLI), skip closing here
        pass
    _mcp_toolboxes.clear()


# Register functions with the llm module
llm.get_mcp_toolbox = get_mcp_toolbox  # type: ignore[attr-defined]
llm.list_mcp_servers = list_mcp_servers  # type: ignore[attr-defined]
llm.clear_mcp_cache = clear_mcp_cache  # type: ignore[attr-defined]


@llm.hookimpl
def register_commands(cli: click.Group) -> None:
    """Register MCP-related commands with the LLM CLI."""

    @cli.group(name="mcp")
    def mcp_group() -> None:
        """Manage MCP (Model Context Protocol) servers."""
        pass

    @mcp_group.command()
    def list_servers() -> None:
        """List all configured MCP servers."""
        config = get_config()

        if not config.servers:
            click.echo("No MCP servers configured.")
            return

        click.echo("Configured MCP servers:")
        for name, server_config in config.servers.items():
            click.echo(f"  {name}: {server_config.transport}")
            if server_config.description:
                click.echo(f"    {server_config.description}")

    @mcp_group.command()
    @click.argument("name")
    @click.option(
        "--transport",
        "-t",
        required=True,
        type=click.Choice(["stdio", "sse", "http"]),
        help="Transport type",
    )
    @click.option("--command", "-c", help="Command to execute (for stdio)")
    @click.option("--args", "-a", multiple=True, help="Arguments to pass to command")
    @click.option("--url", "-u", help="Server URL (for http/sse)")
    @click.option("--header", "-h", multiple=True, help="HTTP header (key:value)")
    @click.option("--env", "-e", multiple=True, help="Environment variable (key=value)")
    @click.option("--description", "-d", help="Human-readable description")
    @click.option("--timeout", default=30, help="Connection timeout in seconds")
    @click.option(
        "--tool-include", multiple=True, help="Tools to include (if specified, only these tools will be exposed)"
    )
    @click.option("--tool-exclude", multiple=True, help="Tools to exclude (these tools will not be exposed)")
    @click.option("--persistent", "-p", is_flag=True, help="Keep a persistent connection open across tool calls")
    def add(
        name: str,
        transport: str,
        command: Optional[str],
        args: tuple,
        url: Optional[str],
        header: tuple,
        env: tuple,
        description: Optional[str],
        timeout: int,
        tool_include: tuple,
        tool_exclude: tuple,
        persistent: bool,
    ) -> None:
        """Add a new MCP server configuration."""

        # Parse headers
        headers = {}
        for h in header:
            if ":" not in h:
                raise click.BadParameter(f"Invalid header format: {h}. Use key:value")
            key, value = h.split(":", 1)
            headers[key.strip()] = value.strip()

        # Parse environment variables
        env_vars = {}
        for e in env:
            if "=" not in e:
                raise click.BadParameter(f"Invalid env var format: {e}. Use key=value")
            key, value = e.split("=", 1)
            env_vars[key.strip()] = value.strip()

        # Convert tool filtering options
        tool_filter_include = list(tool_include) if tool_include else None
        tool_filter_exclude = list(tool_exclude) if tool_exclude else None

        # Create server config
        server_config = MCPServerConfig(
            name=name,
            transport=transport,
            command=command,
            args=list(args),
            url=url,
            headers=headers,
            env=env_vars,
            description=description,
            timeout=timeout,
            tool_filter_include=tool_filter_include,
            tool_filter_exclude=tool_filter_exclude,
            stderr_mode="disable",
            stderr_file=None,
            stderr_append=False,
            persistent=persistent,
        )

        try:
            server_config.validate_config()
        except ValueError as e:
            raise click.BadParameter(str(e))

        # Add to configuration
        config = get_config()
        config.add_server(server_config)
        config.save_to_file()

        click.echo(f"Added MCP server '{name}' with {transport} transport")
        if tool_filter_include:
            click.echo(f"  Tool filter (include): {', '.join(tool_filter_include)}")
        if tool_filter_exclude:
            click.echo(f"  Tool filter (exclude): {', '.join(tool_filter_exclude)}")
        if persistent:
            click.echo("  Persistent: enabled")

    @mcp_group.command()
    @click.argument("name")
    def remove(name: str) -> None:
        """Remove an MCP server configuration."""
        config = get_config()

        if config.remove_server(name):
            config.save_to_file()
            # Clear from cache
            global _mcp_toolboxes
            if name in _mcp_toolboxes:
                # Close persistent session if open
                try:
                    async def _close_one() -> None:
                        toolbox = _mcp_toolboxes[name]
                        if getattr(toolbox.config, "persistent", False):
                            await toolbox.client.aclose()

                    asyncio.run(_close_one())
                except RuntimeError:
                    pass
                del _mcp_toolboxes[name]
            click.echo(f"Removed MCP server '{name}'")
        else:
            click.echo(f"MCP server '{name}' not found")

    @mcp_group.command()
    @click.argument("name")
    def test(name: str) -> None:
        """Test connection to an MCP server."""
        try:
            toolbox = get_mcp_toolbox(name)

            # Initialize the toolbox and list capabilities
            async def test_connection() -> None:
                capabilities = await toolbox.list_capabilities()
                click.echo(f"Successfully connected to MCP server '{name}':")
                click.echo(f"  Tools: {len(capabilities['tools'])}")
                click.echo(f"  Resources: {len(capabilities['resources'])}")
                click.echo(f"  Prompts: {len(capabilities['prompts'])}")

                if capabilities["tools"]:
                    click.echo("  Available tools:")
                    for tool in capabilities["tools"]:
                        click.echo(f"    - {tool}")

            asyncio.run(test_connection())

        except Exception as e:
            click.echo(f"Failed to connect to MCP server '{name}': {e}")

    @mcp_group.command()
    @click.argument("name")
    def info(name: str) -> None:
        """Show detailed information about an MCP server."""
        config = get_config()
        server_config = config.get_server(name)

        if not server_config:
            click.echo(f"MCP server '{name}' not found")
            return

        click.echo(f"MCP Server: {name}")
        click.echo(f"  Transport: {server_config.transport}")

        if server_config.description:
            click.echo(f"  Description: {server_config.description}")

        if server_config.transport == "stdio":
            click.echo(f"  Command: {server_config.command}")
            if server_config.args:
                click.echo(f"  Arguments: {' '.join(server_config.args)}")
            if server_config.env:
                click.echo("  Environment:")
                for key, value in server_config.env.items():
                    click.echo(f"    {key}={value}")

        elif server_config.transport in ("http", "sse"):
            click.echo(f"  URL: {server_config.url}")
            if server_config.headers:
                click.echo("  Headers:")
                for key, value in server_config.headers.items():
                    click.echo(f"    {key}: {value}")

        click.echo(f"  Timeout: {server_config.timeout}s")

        # Show tool filtering configuration
        if server_config.tool_filter_include:
            click.echo(f"  Tool filter (include): {', '.join(server_config.tool_filter_include)}")
        if server_config.tool_filter_exclude:
            click.echo(f"  Tool filter (exclude): {', '.join(server_config.tool_filter_exclude)}")

        # Test connection and show capabilities
        try:
            toolbox = get_mcp_toolbox(name)

            async def show_capabilities() -> None:
                capabilities = await toolbox.list_capabilities()
                click.echo("\nCapabilities:")

                if capabilities["tools"]:
                    click.echo(f"  Tools ({len(capabilities['tools'])}):")
                    for tool in capabilities["tools"]:
                        click.echo(f"    - {tool}")

                if capabilities["resources"]:
                    click.echo(f"  Resources ({len(capabilities['resources'])}):")
                    for resource in capabilities["resources"]:
                        click.echo(f"    - {resource}")

                if capabilities["prompts"]:
                    click.echo(f"  Prompts ({len(capabilities['prompts'])}):")
                    for prompt in capabilities["prompts"]:
                        click.echo(f"    - {prompt}")

            asyncio.run(show_capabilities())

        except Exception as e:
            click.echo(f"\nConnection test failed: {e}")


# Note: MCP toolboxes are created on-demand via llm.get_mcp_toolbox()
# rather than being registered statically, since they depend on configuration
