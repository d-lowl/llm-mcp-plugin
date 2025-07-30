"""MCP client wrapper for connecting to MCP servers."""

import asyncio
import logging
import os
import subprocess
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, List, Optional, Union

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client  
from mcp.client.streamable_http import streamablehttp_client
from mcp import types

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
    
    @asynccontextmanager
    async def connect(self) -> AsyncGenerator[ClientSession, None]:
        """Connect to the MCP server and yield a session.
        
        Yields:
            ClientSession connected to the MCP server
        """
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
    
    def _get_stderr_target(self):
        """Get the appropriate stderr target based on configuration.
        
        Returns:
            subprocess.DEVNULL, subprocess.PIPE, or a file handle
        """
        if self.config.stderr_mode == "disable":
            return subprocess.DEVNULL
        elif self.config.stderr_mode == "terminal":
            return None  # Use default (inherit from parent)
        elif self.config.stderr_mode == "file":
            if not self.config.stderr_file:
                logger.warning("stderr_mode is 'file' but no stderr_file specified, disabling STDERR")
                return subprocess.DEVNULL
            
            # Create directory if it doesn't exist
            stderr_path = os.path.expanduser(self.config.stderr_file)
            os.makedirs(os.path.dirname(stderr_path), exist_ok=True)
            
            # Open file in append or write mode
            mode = "a" if self.config.stderr_append else "w"
            try:
                return open(stderr_path, mode)
            except OSError as e:
                logger.error(f"Failed to open stderr file {stderr_path}: {e}")
                return subprocess.DEVNULL
        else:
            logger.warning(f"Unknown stderr_mode: {self.config.stderr_mode}, disabling STDERR")
            return subprocess.DEVNULL
    
    @asynccontextmanager
    async def _connect_stdio(self) -> AsyncGenerator[ClientSession, None]:
        """Connect using stdio transport with custom STDERR handling."""
        if not self.config.command:
            raise ValueError("Command is required for stdio transport")
        
        # Get stderr target
        stderr_target = self._get_stderr_target()
        stderr_file_handle = None
        
        try:
            # If stderr_target is a file handle, we need to keep track of it
            if hasattr(stderr_target, 'write'):
                stderr_file_handle = stderr_target
            
            # Create custom server parameters
            server_params = StdioServerParameters(
                command=self.config.command,
                args=self.config.args,
                env=self.config.env
            )
            
            # We need to monkey-patch the stdio_client to use our custom stderr handling
            # This is done by temporarily modifying the subprocess creation
            original_create_subprocess_exec = asyncio.create_subprocess_exec
            
            async def custom_create_subprocess_exec(*args, **kwargs):
                # Override stderr in kwargs
                kwargs['stderr'] = stderr_target
                return await original_create_subprocess_exec(*args, **kwargs)
            
            # Temporarily replace the function
            asyncio.create_subprocess_exec = custom_create_subprocess_exec
            
            try:
                async with stdio_client(server_params) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        yield session
            finally:
                # Restore the original function
                asyncio.create_subprocess_exec = original_create_subprocess_exec
                
        finally:
            # Close the stderr file handle if we opened it
            if stderr_file_handle and hasattr(stderr_file_handle, 'close'):
                try:
                    stderr_file_handle.close()
                except:
                    pass
    
    @asynccontextmanager
    async def _connect_sse(self) -> AsyncGenerator[ClientSession, None]:
        """Connect using SSE transport."""
        if not self.config.url:
            raise ValueError("URL is required for SSE transport")
        
        async with sse_client(
            self.config.url,
            headers=self.config.headers
        ) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                yield session
    
    @asynccontextmanager
    async def _connect_http(self) -> AsyncGenerator[ClientSession, None]:
        """Connect using HTTP transport."""
        if not self.config.url:
            raise ValueError("URL is required for HTTP transport")
        
        async with streamablehttp_client(
            self.config.url,
            headers=self.config.headers
        ) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                yield session
    
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
            return self._tools_cache
    
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
            return self._resources_cache
    
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
            return self._prompts_cache
    
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