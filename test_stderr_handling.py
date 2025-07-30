#!/usr/bin/env python3
"""Test script to verify STDERR handling functionality for MCP servers."""

import asyncio
import json
import os
import tempfile
import time
from pathlib import Path

from llm_mcp_plugin.config import MCPServerConfig
from llm_mcp_plugin.mcp_client import MCPClient


# Simple test server that writes to STDERR
TEST_SERVER_SCRIPT = '''#!/usr/bin/env python3
import sys
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("test-stderr-server")

# Write some test messages to stderr
print("This is a test STDERR message from MCP server", file=sys.stderr)
print("Another STDERR line for testing", file=sys.stderr)

@mcp.tool()
def test_tool() -> str:
    """A simple test tool that also writes to stderr."""
    print("Tool execution STDERR message", file=sys.stderr)
    return "Tool executed successfully"

if __name__ == "__main__":
    mcp.run(transport="stdio")
'''


async def test_stderr_disable():
    """Test STDERR disabled mode."""
    print("Testing STDERR disable mode...")
    
    # Create temporary server script
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(TEST_SERVER_SCRIPT)
        server_script = f.name
    
    try:
        # Configure server with STDERR disabled
        config = MCPServerConfig(
            name="test-stderr-disable",
            transport="stdio",
            command="python",
            args=[server_script],
            stderr_mode="disable"
        )
        
        client = MCPClient(config)
        
        # Connect and call a tool
        async with client.connect() as session:
            tools_response = await session.list_tools()
            tools = tools_response.tools
            print(f"Found {len(tools)} tools")
            
            # Call the test tool
            result = await session.call_tool("test_tool", {})
            print(f"Tool result: {result}")
        
        print("✓ STDERR disable test completed - no stderr output should be visible")
        
    finally:
        os.unlink(server_script)


async def test_stderr_to_file():
    """Test STDERR to file mode."""
    print("\nTesting STDERR to file mode...")
    
    # Create temporary server script
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(TEST_SERVER_SCRIPT)
        server_script = f.name
    
    # Create temporary stderr file
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        stderr_file = f.name
    
    try:
        # Configure server with STDERR to file
        config = MCPServerConfig(
            name="test-stderr-file",
            transport="stdio",
            command="python",
            args=[server_script],
            stderr_mode="file",
            stderr_file=stderr_file,
            stderr_append=False
        )
        
        client = MCPClient(config)
        
        # Connect and call a tool
        async with client.connect() as session:
            tools_response = await session.list_tools()
            tools = tools_response.tools
            print(f"Found {len(tools)} tools")
            
            # Call the test tool
            result = await session.call_tool("test_tool", {})
            print(f"Tool result: {result}")
        
        # Check if stderr was written to file
        if os.path.exists(stderr_file):
            with open(stderr_file, 'r') as f:
                stderr_content = f.read()
            print(f"✓ STDERR file test completed")
            print(f"STDERR content written to {stderr_file}:")
            print(stderr_content)
        else:
            print("✗ STDERR file was not created")
        
    finally:
        os.unlink(server_script)
        if os.path.exists(stderr_file):
            os.unlink(stderr_file)


async def test_stderr_terminal():
    """Test STDERR to terminal mode."""
    print("\nTesting STDERR to terminal mode...")
    
    # Create temporary server script
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(TEST_SERVER_SCRIPT)
        server_script = f.name
    
    try:
        # Configure server with STDERR to terminal
        config = MCPServerConfig(
            name="test-stderr-terminal",
            transport="stdio",
            command="python",
            args=[server_script],
            stderr_mode="terminal"
        )
        
        client = MCPClient(config)
        
        print("You should see STDERR messages in the terminal below:")
        
        # Connect and call a tool
        async with client.connect() as session:
            tools_response = await session.list_tools()
            tools = tools_response.tools
            print(f"Found {len(tools)} tools")
            
            # Call the test tool
            result = await session.call_tool("test_tool", {})
            print(f"Tool result: {result}")
        
        print("✓ STDERR terminal test completed - stderr should be visible above")
        
    finally:
        os.unlink(server_script)


async def test_config_validation():
    """Test configuration validation."""
    print("\nTesting configuration validation...")
    
    # Test invalid config - file mode without stderr_file
    try:
        config = MCPServerConfig(
            name="test-invalid",
            transport="stdio",
            command="python",
            args=["test.py"],
            stderr_mode="file"
            # Missing stderr_file
        )
        config.validate_config()
        print("✗ Configuration validation failed - should have raised error")
    except ValueError as e:
        print(f"✓ Configuration validation working: {e}")
    
    # Test valid config
    try:
        config = MCPServerConfig(
            name="test-valid",
            transport="stdio",
            command="python",
            args=["test.py"],
            stderr_mode="file",
            stderr_file="/tmp/test.log"
        )
        config.validate_config()
        print("✓ Valid configuration accepted")
    except ValueError as e:
        print(f"✗ Valid configuration rejected: {e}")


async def main():
    """Run all tests."""
    print("=" * 50)
    print("MCP STDERR Handling Tests")
    print("=" * 50)
    
    await test_config_validation()
    await test_stderr_disable()
    await test_stderr_to_file()
    await test_stderr_terminal()
    
    print("\n" + "=" * 50)
    print("All tests completed!")


if __name__ == "__main__":
    asyncio.run(main())