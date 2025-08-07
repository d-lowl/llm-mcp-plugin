"""Configuration classes for MCP server definitions."""

import json
from pathlib import Path
from typing import Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field


class MCPServerConfig(BaseModel):
    """Configuration for an MCP server."""

    name: str = Field(description="Unique name for the MCP server")
    transport: str = Field(
        description="Transport type: 'stdio', 'sse', or 'http'",
        pattern="^(stdio|sse|http)$",
    )

    # Stdio transport options
    command: Optional[str] = Field(None, description="Command to execute (for stdio)")
    args: List[str] = Field(default_factory=list, description="Arguments to pass to command")
    env: Dict[str, str] = Field(default_factory=dict, description="Environment variables")

    # HTTP/SSE transport options
    url: Optional[str] = Field(None, description="Server URL (for http/sse)")
    headers: Dict[str, str] = Field(default_factory=dict, description="HTTP headers")

    # General options
    timeout: int = Field(30, description="Connection timeout in seconds")
    description: Optional[str] = Field(None, description="Human-readable description")

    # Tool filtering options
    tool_filter_include: Optional[List[str]] = Field(
        None, 
        description="List of tool names to include (if specified, only these tools will be exposed)"
    )
    tool_filter_exclude: Optional[List[str]] = Field(
        None, 
        description="List of tool names to exclude (these tools will not be exposed)"
    )

    # STDERR handling options
    stderr_mode: Literal["disable", "file", "terminal"] = Field(
        "disable",
        description=(
            "How to handle STDERR: 'disable' (default), 'file' (redirect to file), " "'terminal' (display in terminal)"
        ),
    )
    stderr_file: Optional[str] = Field(
        None,
        description="File path to redirect STDERR to (only used when stderr_mode='file')",
    )
    stderr_append: bool = Field(
        False,
        description="Whether to append to stderr_file (True) or overwrite it (False)",
    )

    def validate_config(self) -> None:
        """Validate that required fields are present for the transport type."""
        if self.transport == "stdio":
            if not self.command:
                raise ValueError("Command is required for stdio transport")
        elif self.transport in ("http", "sse"):
            if not self.url:
                raise ValueError("URL is required for http/sse transport")

        # Validate STDERR configuration
        if self.stderr_mode == "file" and not self.stderr_file:
            raise ValueError("stderr_file is required when stderr_mode='file'")

    def should_include_tool(self, tool_name: str) -> bool:
        """Check if a tool should be included based on filter configuration.
        
        Args:
            tool_name: Name of the tool to check
            
        Returns:
            True if the tool should be included, False otherwise
        """
        # If include list is specified, tool must be in it
        if self.tool_filter_include is not None:
            if tool_name not in self.tool_filter_include:
                return False
        
        # If exclude list is specified, tool must not be in it
        if self.tool_filter_exclude is not None:
            if tool_name in self.tool_filter_exclude:
                return False
        
        return True


class MCPPluginConfig(BaseModel):
    """Configuration for the entire MCP plugin."""

    servers: Dict[str, MCPServerConfig] = Field(default_factory=dict, description="Dictionary of server configurations")

    @classmethod
    def load_from_file(cls, config_path: Optional[Union[str, Path]] = None) -> "MCPPluginConfig":
        """Load configuration from a JSON file.

        Args:
            config_path: Path to config file. If None, uses default location.

        Returns:
            MCPPluginConfig instance
        """
        if config_path is None:
            config_path = cls.get_default_config_path()

        config_path = Path(config_path)

        if not config_path.exists():
            return cls()

        try:
            with open(config_path, "r") as f:
                data = json.load(f)

            # Convert server configs to MCPServerConfig objects
            servers = {}
            for name, server_data in data.get("servers", {}).items():
                server_data["name"] = name
                servers[name] = MCPServerConfig(**server_data)

            return cls(servers=servers)
        except (json.JSONDecodeError, Exception) as e:
            raise ValueError(f"Failed to load config from {config_path}: {e}")

    def save_to_file(self, config_path: Optional[Union[str, Path]] = None) -> None:
        """Save configuration to a JSON file.

        Args:
            config_path: Path to save config file. If None, uses default location.
        """
        if config_path is None:
            config_path = self.get_default_config_path()

        config_path = Path(config_path)
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to dict format for JSON serialization
        data = {"servers": {name: server.model_dump(exclude={"name"}) for name, server in self.servers.items()}}

        with open(config_path, "w") as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def get_default_config_path() -> Path:
        """Get the default configuration file path."""
        config_dir = Path.home() / ".config" / "llm"
        return config_dir / "mcp_servers.json"

    def add_server(self, server_config: MCPServerConfig) -> None:
        """Add a server configuration."""
        server_config.validate_config()
        self.servers[server_config.name] = server_config

    def remove_server(self, name: str) -> bool:
        """Remove a server configuration.

        Args:
            name: Server name to remove

        Returns:
            True if server was removed, False if not found
        """
        if name in self.servers:
            del self.servers[name]
            return True
        return False

    def get_server(self, name: str) -> Optional[MCPServerConfig]:
        """Get a server configuration by name."""
        return self.servers.get(name)
