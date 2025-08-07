"""MCP client wrapper for connecting to MCP servers."""

import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, List, Optional, TextIO, cast

from mcp import ClientSession, StdioServerParameters, types
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client

from .config import MCPServerConfig

logger = logging.getLogger(__name__)


class MCPClient:
    """Wrapper for MCP client sessions with support for multiple transports."""

    def __init__(self, config: MCPServerConfig):
        """Initialize MCP client with server configuration.

        Args:
            config: MCP server configuration
        """
        self.config = config
        self._session: Optional[ClientSession] = None
        self._tools_cache: Optional[List[types.Tool]] = None
        self._resources_cache: Optional[List[types.Resource]] = None
        self._prompts_cache: Optional[List[types.Prompt]] = None
        # Persistent connection internals
        self._transport_cm: Optional[Any] = None
        self._session_cm: Optional[Any] = None
        self._stderr_target: Optional[TextIO] = None
        try:
            import asyncio

            self._connect_lock = asyncio.Lock()
        except Exception:
            self._connect_lock = None  # Fallback for environments without asyncio loop yet

    @asynccontextmanager
    async def connect(self) -> AsyncGenerator[ClientSession, None]:
        """Connect to the MCP server and yield a session.

        Yields:
            ClientSession connected to the MCP server
        """
        # Reuse persistent session if configured
        if getattr(self.config, "persistent", False):
            await self._ensure_persistent_session()
            assert self._session is not None
            yield self._session
            return

        if self.config.transport == "stdio":
            async with self._connect_stdio() as session:
                yield session
        elif self.config.transport == "sse":
            async with self._connect_sse() as session:
                yield session
        elif self.config.transport == "http":
            async with self._connect_http() as session:
                yield session
        else:
            raise ValueError(f"Unsupported transport: {self.config.transport}")

    def _get_stderr_target(self) -> TextIO:
        """Get the appropriate stderr target based on configuration.

        Returns:
            A TextIO object for stderr handling
        """
        if self.config.stderr_mode == "disable":
            # Return devnull as a TextIO object
            return cast(TextIO, open(os.devnull, "w"))
        elif self.config.stderr_mode == "terminal":
            return sys.stderr  # Use default (inherit from parent)
        elif self.config.stderr_mode == "file":
            if not self.config.stderr_file:
                logger.warning("stderr_mode is 'file' but no stderr_file specified, disabling STDERR")
                return cast(TextIO, open(os.devnull, "w"))

            # Create directory if it doesn't exist
            stderr_path = os.path.expanduser(self.config.stderr_file)
            os.makedirs(os.path.dirname(stderr_path), exist_ok=True)

            # Open file in append or write mode
            mode = "a" if self.config.stderr_append else "w"
            try:
                return cast(TextIO, open(stderr_path, mode))
            except OSError as e:
                logger.error(f"Failed to open stderr file {stderr_path}: {e}")
                return cast(TextIO, open(os.devnull, "w"))
        else:
            logger.warning(f"Unknown stderr_mode: {self.config.stderr_mode}, disabling STDERR")
            return cast(TextIO, open(os.devnull, "w"))

    @asynccontextmanager
    async def _connect_stdio(self) -> AsyncGenerator[ClientSession, None]:
        """Connect using stdio transport with custom STDERR handling."""
        if not self.config.command:
            raise ValueError("Command is required for stdio transport")

        # Get stderr target
        stderr_target = self._get_stderr_target()

        try:
            # Create server parameters
            # Resolve python command to current interpreter for portability
            command_to_use = self.config.command
            try:
                import shutil

                if command_to_use in ("python", "python3") and shutil.which(command_to_use) is None:
                    command_to_use = sys.executable
            except Exception:
                pass

            server_params = StdioServerParameters(
                command=command_to_use, args=self.config.args, env=self.config.env
            )

            # Use stdio_client with custom errlog parameter
            async with stdio_client(server_params, errlog=stderr_target) as (
                read,
                write,
            ):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    yield session

        finally:
            # Close the stderr file handle if we opened it (but not sys.stderr)
            if stderr_target != sys.stderr:
                try:
                    stderr_target.close()
                except Exception:
                    pass

    @asynccontextmanager
    async def _connect_sse(self) -> AsyncGenerator[ClientSession, None]:
        """Connect using SSE transport."""
        if not self.config.url:
            raise ValueError("URL is required for SSE transport")

        async with sse_client(self.config.url, headers=self.config.headers) as (
            read,
            write,
        ):
            async with ClientSession(read, write) as session:
                await session.initialize()
                yield session

    @asynccontextmanager
    async def _connect_http(self) -> AsyncGenerator[ClientSession, None]:
        """Connect using HTTP transport."""
        if not self.config.url:
            raise ValueError("URL is required for HTTP transport")

        async with streamablehttp_client(self.config.url, headers=self.config.headers) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                yield session

    async def _ensure_persistent_session(self) -> None:
        """Ensure a persistent session is established and ready to use."""
        if self._session is not None:
            return
        lock = getattr(self, "_connect_lock", None)
        if lock is not None:
            async with lock:
                if self._session is not None:
                    return
                await self._open_persistent()
        else:
            # Fallback without lock
            await self._open_persistent()

    async def _open_persistent(self) -> None:
        """Open the persistent transport and session, storing context managers for later close."""
        # Prepare stderr for stdio early so it stays open
        stderr_target = None
        if self.config.transport == "stdio":
            stderr_target = self._get_stderr_target()
        self._stderr_target = stderr_target

        if self.config.transport == "stdio":
            if not self.config.command:
                raise ValueError("Command is required for stdio transport")
            # Resolve python command to current interpreter for portability
            command_to_use = self.config.command
            try:
                import shutil
                if command_to_use in ("python", "python3") and shutil.which(command_to_use) is None:
                    command_to_use = sys.executable
            except Exception:
                pass
            server_params = StdioServerParameters(
                command=command_to_use, args=self.config.args, env=self.config.env
            )
            transport_cm = stdio_client(server_params, errlog=stderr_target)
            read, write = await transport_cm.__aenter__()
        elif self.config.transport == "sse":
            if not self.config.url:
                raise ValueError("URL is required for SSE transport")
            transport_cm = sse_client(self.config.url, headers=self.config.headers)
            read, write = await transport_cm.__aenter__()
        elif self.config.transport == "http":
            if not self.config.url:
                raise ValueError("URL is required for HTTP transport")
            transport_cm = streamablehttp_client(self.config.url, headers=self.config.headers)
            read, write, _ = await transport_cm.__aenter__()
        else:
            raise ValueError(f"Unsupported transport: {self.config.transport}")

        session_cm = ClientSession(read, write)
        session = await session_cm.__aenter__()
        await session.initialize()

        self._transport_cm = transport_cm
        self._session_cm = session_cm
        self._session = session
        logger.info("Established persistent MCP session")

    async def aclose(self) -> None:
        """Close any persistent session and transport, if open."""
        lock = getattr(self, "_connect_lock", None)
        if lock is not None:
            async with lock:
                await self._close_persistent_locked()
        else:
            await self._close_persistent_locked()

    async def _close_persistent_locked(self) -> None:
        session_cm = self._session_cm
        transport_cm = self._transport_cm
        stderr_target = self._stderr_target

        self._session_cm = None
        self._transport_cm = None
        self._stderr_target = None
        self._session = None

        try:
            if session_cm is not None:
                await session_cm.__aexit__(None, None, None)
        finally:
            if transport_cm is not None:
                try:
                    await transport_cm.__aexit__(None, None, None)
                finally:
                    if stderr_target is not None and stderr_target is not sys.stderr:
                        try:
                            stderr_target.close()
                        except Exception:
                            pass
        logger.info("Closed persistent MCP session")

    async def get_tools(self, force_refresh: bool = False) -> List[types.Tool]:
        """Get available tools from the MCP server.

        Args:
            force_refresh: If True, bypass cache and fetch fresh data

        Returns:
            List of available tools
        """
        if not force_refresh and self._tools_cache is not None:
            return self._tools_cache

        async with self.connect() as session:
            tools_response = await session.list_tools()
            self._tools_cache = tools_response.tools
            return self._tools_cache or []

    async def get_resources(self, force_refresh: bool = False) -> List[types.Resource]:
        """Get available resources from the MCP server.

        Args:
            force_refresh: If True, bypass cache and fetch fresh data

        Returns:
            List of available resources
        """
        if not force_refresh and self._resources_cache is not None:
            return self._resources_cache

        async with self.connect() as session:
            resources_response = await session.list_resources()
            self._resources_cache = resources_response.resources
            return self._resources_cache or []

    async def get_prompts(self, force_refresh: bool = False) -> List[types.Prompt]:
        """Get available prompts from the MCP server.

        Args:
            force_refresh: If True, bypass cache and fetch fresh data

        Returns:
            List of available prompts
        """
        if not force_refresh and self._prompts_cache is not None:
            return self._prompts_cache

        async with self.connect() as session:
            prompts_response = await session.list_prompts()
            self._prompts_cache = prompts_response.prompts
            return self._prompts_cache or []

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> types.CallToolResult:
        """Call a tool on the MCP server.

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            Tool execution result
        """
        async with self.connect() as session:
            return await session.call_tool(name, arguments)

    async def read_resource(self, uri: str) -> types.ReadResourceResult:
        """Read a resource from the MCP server.

        Args:
            uri: Resource URI

        Returns:
            Resource content
        """
        async with self.connect() as session:
            from pydantic import AnyUrl

            return await session.read_resource(AnyUrl(uri))

    async def get_prompt(self, name: str, arguments: Optional[Dict[str, str]] = None) -> types.GetPromptResult:
        """Get a prompt from the MCP server.

        Args:
            name: Prompt name
            arguments: Prompt arguments

        Returns:
            Prompt result
        """
        async with self.connect() as session:
            return await session.get_prompt(name, arguments)

    def clear_cache(self) -> None:
        """Clear all cached data."""
        self._tools_cache = None
        self._resources_cache = None
        self._prompts_cache = None
