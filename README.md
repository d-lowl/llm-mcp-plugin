# LLM MCP Plugin

A plugin for the [LLM](https://llm.datasette.io/) command-line tool that enables using [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) servers as toolboxes in conversations.

## Features

- **Dynamic MCP Server Integration**: Connect to any MCP server and expose its tools as LLM toolbox methods
- **Multiple Transport Support**: Works with stdio, SSE, and HTTP-based MCP servers  
- **Automatic Tool Discovery**: Automatically converts MCP tools into callable methods
- **Resource & Prompt Access**: Expose MCP resources and prompts through the toolbox
- **Configuration-Driven**: Easy setup for different MCP servers via configuration files

## Installation

```bash
pip install llm-mcp-plugin
```

## Quick Start

1. **Configure an MCP server** in your LLM configuration:

```bash
# Add a Toggl Track MCP server
llm mcp add toggl \
  --transport stdio \
  --command "node" \
  --args "/path/to/toggl-track-mcp/dist/index.js"
```

2. **Use the MCP toolbox in conversations**:

```python
import llm

# Get a model and create a conversation with MCP toolbox
model = llm.get_model("gpt-4")
mcp_toolbox = llm.get_mcp_toolbox("toggl")

conversation = model.conversation(tools=[mcp_toolbox])

# Use MCP tools through natural language
response = conversation.chain("Create a new time entry for working on documentation")
print(response.text())
```

## Configuration

### Stdio Transport (recommended for local servers)

```bash
llm mcp add my-server \
  --transport stdio \
  --command "python" \
  --args "/path/to/server.py"
```

### HTTP Transport

```bash
llm mcp add remote-server \
  --transport http \
  --url "http://localhost:8000/mcp"
```

### Configuration File

You can also create a configuration file at `~/.config/llm/mcp_servers.json`:

```json
{
  "servers": {
    "toggl": {
      "transport": "stdio",
      "command": "node",
      "args": ["/path/to/toggl-track-mcp/dist/index.js"],
      "env": {}
    },
    "weather": {
      "transport": "http", 
      "url": "http://localhost:8000/mcp",
      "headers": {
        "Authorization": "Bearer your-token"
      }
    }
  }
}
```

## Examples

### Time Tracking with Toggl

```python
import llm

model = llm.get_model("claude-3.5-sonnet")
toggl = llm.get_mcp_toolbox("toggl")

conversation = model.conversation(tools=[toggl])

# Start tracking time
response = conversation.chain(
    "Start a timer for 'Writing documentation' in the 'Documentation' project"
)

# Get current status
response = conversation.chain("What's my current time entry?")

# Generate a time report
response = conversation.chain("Show me my time entries for today")
```

### File System Operations

```python
import llm

model = llm.get_model("gpt-4")
filesystem = llm.get_mcp_toolbox("filesystem")

conversation = model.conversation(tools=[filesystem])

response = conversation.chain(
    "List all Python files in the current directory and show me their sizes"
)
```

## Supported MCP Servers

This plugin works with any MCP server that follows the [Model Context Protocol specification](https://spec.modelcontextprotocol.io/). Some examples:

- [Toggl Track MCP](https://github.com/fuzzylabs/toggl-track-mcp) - Time tracking integration
- [Filesystem MCP](https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem) - File system operations
- [Git MCP](https://github.com/modelcontextprotocol/servers/tree/main/src/git) - Git repository management
- [SQLite MCP](https://github.com/modelcontextprotocol/servers/tree/main/src/sqlite) - Database operations

## Advanced Usage

### Custom Server Configuration

```python
import llm
from llm_mcp_plugin import MCPToolbox

# Create a toolbox with custom configuration
toolbox = MCPToolbox(
    name="custom-server",
    transport="stdio",
    command="python",
    args=["/path/to/server.py"],
    env={"API_KEY": "your-key"}
)

model = llm.get_model("gpt-4")
conversation = model.conversation(tools=[toolbox])
```

### Async Usage

```python
import asyncio
import llm

async def use_mcp_async():
    model = llm.get_async_model("claude-3.5-sonnet")
    mcp_toolbox = llm.get_mcp_toolbox("toggl")
    
    conversation = model.conversation(tools=[mcp_toolbox])
    
    response = await conversation.chain("Get my current time tracking status")
    print(response.text())

asyncio.run(use_mcp_async())
```

## Development

```bash
git clone https://github.com/your-repo/llm-mcp-plugin
cd llm-mcp-plugin
pip install -e ".[dev]"
pytest
```

## License

MIT License. See [LICENSE](LICENSE) for details.

## Contributing

Contributions welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.
