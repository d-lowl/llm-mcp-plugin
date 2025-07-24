"""MCPToolbox class that converts MCP servers into LLM toolboxes."""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Union

import llm
from mcp import types

from .config import MCPServerConfig
from .mcp_client import MCPClient

logger = logging.getLogger(__name__)


class MCPToolbox(llm.Toolbox):
    """LLM Toolbox that wraps an MCP server and exposes its tools as methods."""
    
    def __init__(self, config: MCPServerConfig):
        """Initialize MCPToolbox with server configuration.
        
        Args:
            config: MCP server configuration
        """
        self.config = config
        self.client = MCPClient(config)
        self._tools: Dict[str, types.Tool] = {}
        self._resources: Dict[str, types.Resource] = {}
        self._prompts: Dict[str, types.Prompt] = {}
        self._initialized = False
        
        # Set common attributes that might be accessed without initialization
        self.__name__ = f"MCP_{config.name}"
        self.tool_name = f"MCP_{config.name}"
    
    async def _ensure_initialized(self) -> None:
        """Ensure the toolbox is initialized with tools from the MCP server."""
        if self._initialized:
            return
        
        try:
            # Load capabilities from the MCP server, handling cases where some methods aren't supported
            tools = []
            resources = []
            prompts = []
            
            # Try to get tools
            try:
                tools = await self.client.get_tools()
            except Exception as e:
                logger.warning(f"Server '{self.config.name}' doesn't support tools: {e}")
            
            # Cache by name for quick lookup
            self._tools = {tool.name: tool for tool in tools}
            
            # Dynamically add methods to this toolbox instance
            self._add_tool_methods()
            
            self._initialized = True
            logger.info(f"Initialized MCP toolbox '{self.config.name}' with {len(tools)} tools, {len(resources)} resources, {len(prompts)} prompts")
            
        except Exception as e:
            logger.error(f"Failed to initialize MCP toolbox '{self.config.name}': {e}")
            # Don't raise - just mark as failed initialization
            self._initialized = True  # Mark as initialized even if failed to avoid retry loops
            logger.warning(f"MCP toolbox '{self.config.name}' initialized with limited functionality")
    
    def _add_tool_methods(self) -> None:
        """Dynamically add tool methods to the toolbox."""
        for tool_name, tool in self._tools.items():
            # Create a method that calls the MCP tool
            def make_tool_method(tool_obj: types.Tool):
                async def tool_method(**kwargs) -> str:
                    """Dynamically generated tool method."""
                    try:
                        result = await self.client.call_tool(tool_obj.name, kwargs)
                        
                        # Format the result for LLM consumption
                        if hasattr(result, 'structuredContent') and result.structuredContent:
                            # Return structured content if available
                            return json.dumps(result.structuredContent, indent=2)
                        elif result.content:
                            # Return text content
                            text_parts = []
                            for content in result.content:
                                if isinstance(content, types.TextContent):
                                    text_parts.append(content.text)
                                elif isinstance(content, types.ImageContent):
                                    text_parts.append(f"[Image: {content.mimeType}]")
                                elif isinstance(content, types.EmbeddedResource):
                                    if isinstance(content.resource, types.TextResourceContents):
                                        text_parts.append(f"[Resource {content.resource.uri}]: {content.resource.text}")
                                    else:
                                        text_parts.append(f"[Resource {content.resource.uri}]")
                            return "\n".join(text_parts)
                        else:
                            return "Tool executed successfully (no output)"
                            
                    except Exception as e:
                        logger.error(f"Error calling tool {tool_obj.name}: {e}")
                        return f"Error: {str(e)}"
                
                # Set method attributes
                tool_method.__name__ = tool_obj.name
                tool_method.__doc__ = tool_obj.description or f"Call the {tool_obj.name} tool"
                
                return tool_method
            
            # Add the method to this instance
            method = make_tool_method(tool)
            setattr(self, tool_name, method)
    
    def __getattribute__(self, name: str) -> Any:
        """Override attribute access to ensure initialization."""
        # Skip initialization for internal attributes or methods we know exist
        if (name.startswith('_') or 
            name in ['config', 'client', 'get_description', 'list_capabilities', '__name__', 'tool_name', '__class__', '__dict__', '__module__'] or
            hasattr(llm.Toolbox, name)):
            return super().__getattribute__(name)
        
        # For dynamic methods, ensure we're initialized
        try:
            initialized = super().__getattribute__('_initialized')
        except AttributeError:
            initialized = False
            
        if not initialized:
            # Try to initialize, but don't crash if we can't
            try:
                # Check if we're in an async context
                try:
                    loop = asyncio.get_running_loop()
                    # We're in an async context, can't run sync initialization
                    logger.warning(f"Cannot initialize MCP toolbox '{self.config.name}' in async context")
                except RuntimeError:
                    # No running loop, we can create one and run initialization
                    try:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        loop.run_until_complete(self._ensure_initialized())
                        loop.close()
                    except Exception as init_error:
                        logger.warning(f"Failed to initialize MCP toolbox '{self.config.name}': {init_error}")
                        # Mark as initialized to avoid infinite retry
                        super().__setattr__('_initialized', True)
            except Exception as e:
                logger.warning(f"Error during MCP toolbox initialization: {e}")
                # Mark as initialized to avoid infinite retry
                super().__setattr__('_initialized', True)
        
        # Try to get the attribute, return a safe default if it doesn't exist
        try:
            return super().__getattribute__(name)
        except AttributeError:
            # Return a placeholder method for unknown dynamic methods
            def placeholder_method(*args, **kwargs):
                return f"MCP toolbox '{self.config.name}' method '{name}' not available (initialization failed or method not found)"
            return placeholder_method
    
    async def list_capabilities(self) -> Dict[str, List[str]]:
        """List all available capabilities from the MCP server.
        
        Returns:
            Dictionary with tools, resources, and prompts lists
        """
        await self._ensure_initialized()
        
        return {
            "tools": list(self._tools.keys()),
            "resources": list(self._resources.keys()),
            "prompts": list(self._prompts.keys())
        }
    
    def method_tools(self):
        """Return a generator of llm.Tool() for each method."""
        # Ensure we're initialized first
        if not self._initialized:
            try:
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self._ensure_initialized())
                loop.close()
            except Exception as e:
                logger.warning(f"Failed to initialize MCP toolbox for method_tools: {e}")
                return
        
        # Convert MCP tools to LLM tools
        for tool_name, mcp_tool in self._tools.items():
            # Get the dynamically created method
            if hasattr(self, tool_name):
                tool_method = getattr(self, tool_name)
                
                # Create an llm.Tool from the method
                try:
                    llm_tool = llm.Tool(
                        name=tool_name,
                        description=mcp_tool.description or f"MCP tool: {tool_name}",
                        input_schema=mcp_tool.inputSchema,
                        implementation=tool_method
                    )
                    yield llm_tool
                except Exception as e:
                    logger.warning(f"Failed to create tool for {tool_name}: {e}")
        
    
    def get_description(self) -> str:
        """Get a description of this toolbox."""
        desc = f"MCP Toolbox for '{self.config.name}'"
        if self.config.description:
            desc += f": {self.config.description}"
        return desc 