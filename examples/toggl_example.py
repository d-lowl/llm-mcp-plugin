#!/usr/bin/env python3
"""
Example script demonstrating the use of Toggl Track MCP server with LLM.

This example assumes you have:
1. The toggl-track-mcp server installed and configured
2. A Toggl API token configured for the server
3. This plugin installed: pip install llm-mcp-plugin
"""

import asyncio
import llm
from llm_mcp_plugin import MCPServerConfig


async def main():
    """Demonstrate using Toggl Track MCP server as an LLM toolbox."""
    
    # Configure the Toggl Track MCP server
    # You'll need to adjust the path to match your installation
    toggl_config = MCPServerConfig(
        name="toggl",
        transport="stdio",
        command="node",
        args=["/path/to/toggl-track-mcp/dist/index.js"],
        env={
            "TOGGL_API_TOKEN": "your_toggl_api_token_here"
        },
        description="Toggl Track time tracking integration"
    )
    
    # Add the server to the configuration
    from llm_mcp_plugin.plugin import get_config
    config = get_config()
    config.add_server(toggl_config)
    config.save_to_file()
    
    print("✓ Configured Toggl Track MCP server")
    
    # Get the MCP toolbox
    toggl_toolbox = llm.get_mcp_toolbox("toggl")
    
    # Initialize the toolbox
    await toggl_toolbox._ensure_initialized()
    
    # List available capabilities
    capabilities = await toggl_toolbox.list_capabilities()
    print(f"\n📋 Available capabilities:")
    print(f"  Tools: {capabilities['tools']}")
    print(f"  Resources: {capabilities['resources']}")
    print(f"  Prompts: {capabilities['prompts']}")
    
    # Use the toolbox with an LLM model
    model = llm.get_model("gpt-4o-mini")  # or whatever model you prefer
    conversation = model.conversation(tools=[toggl_toolbox])
    
    print("\n🤖 Starting conversation with LLM using Toggl tools...")
    
    # Example conversations
    examples = [
        "What time entries do I have for today?",
        "Create a time entry for 'Documentation work' for 2 hours",
        "What projects do I have available?",
        "Show me my time tracking summary for this week"
    ]
    
    for i, prompt in enumerate(examples, 1):
        print(f"\n--- Example {i}: {prompt} ---")
        try:
            response = conversation.chain(prompt)
            print(f"Response: {response.text()}")
        except Exception as e:
            print(f"Error: {e}")
    
    print("\n✅ Demo completed!")


def simple_sync_example():
    """Simple synchronous example for quick testing."""
    # This shows how to use the plugin once configured
    try:
        # List configured servers
        servers = llm.list_mcp_servers()
        print(f"Configured MCP servers: {servers}")
        
        if "toggl" in servers:
            print("✓ Toggl server found in configuration")
            
            # You can now use it in conversations:
            # model = llm.get_model("gpt-4o-mini")
            # toggl = llm.get_mcp_toolbox("toggl")
            # conversation = model.conversation(tools=[toggl])
            # response = conversation.chain("Show me my current time tracking status")
            
        else:
            print("❌ Toggl server not configured. Run the async main() first.")
            
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "sync":
        simple_sync_example()
    else:
        print("🚀 Running Toggl Track MCP demo...")
        print("Make sure to update the paths and API token in the script!")
        asyncio.run(main()) 