# LLM MCP Plugin

[![CI](https://github.com/d-lowl/llm-mcp-plugin/actions/workflows/ci.yml/badge.svg)](https://github.com/d-lowl/llm-mcp-plugin/actions/workflows/ci.yml)

**IMPORTANT: This is a very early version of the MCP wrapper for [llm](https://llm.datasette.io/) and [Bespoken](https://bespoken.ai/), largely written by Claude and barely tested. Proceed with caution.**

A plugin for the [LLM](https://llm.datasette.io/) command-line tool that enables using [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) servers as toolboxes in conversations.

## Features

- **Dynamic MCP Server Integration**: Connect to any MCP server and expose its tools as LLM toolbox methods
- **Multiple Transport Support**: Works with stdio, SSE, and HTTP-based MCP servers
- **Automatic Tool Discovery**: Automatically converts MCP tools into callable methods
- **Tool Filtering**: Filter exposed tools by name using include/exclude lists for enhanced security
- **Resource & Prompt Access**: Expose MCP resources and prompts through the toolbox
- **Configuration-Driven**: Easy setup for different MCP servers via configuration files
- **STDERR Handling**: Control how MCP server error output is handled (disable, redirect to file, or display in terminal)

## Installation

```bash
uv add git+https://github.com/d-lowl/llm-mcp-plugin.git
```

## Development

### Setup

To set up the development environment:

```bash
# Install all dependencies (including linting tools and pre-commit)
uv sync

# Install pre-commit hooks for automatic code quality checks
uv run pre-commit install

# (Optional) Run pre-commit against all files
uv run pre-commit run --all-files
```

The pre-commit configuration includes:
- **Black** - Code formatting
- **isort** - Import sorting
- **mypy** - Type checking
- **flake8** - Linting
- **bandit** - Security checks

## Quick Start

Usage in Bespoken:

```python
mcp_toolbox = MCPToolbox(
    config=MCPServerConfig(
        name="notion",
        transport="stdio",
        command="npx",
        args=["-y", "@notionhq/notion-mcp-server"],
        env={
            "OPENAPI_MCP_HEADERS": f'{{"Authorization": "Bearer {NOTION_API_KEY}", "Notion-Version": "2022-06-28" }}'
        }
    )
)

chat(
    model_name="anthropic/claude-3-5-sonnet-20240620",
    tools=[TodoTools(), mcp_toolbox],
    system_prompt=SYSTEM_PROMPT,
    debug=True,
    slash_commands={
        "/thinking": "Let me think through this step by step:",
        "/role": set_role,
        "/whoami": whoami,
    },
)
```

(I haven't done any testing in bare llm yet, but it should work.)

## Examples

This repo contains an example Bespoken agent script for Notion.

```bash
export NOTION_API_KEY=your-notion-api-key
export ANTHROPIC_API_KEY=your-anthropic-api-key

./notion_example.py
```

![Notion example](./images/notion_example.png)

## Tool Filtering

The plugin supports filtering tools by name to enhance security and control which tools are exposed. You can use:

- **Include filters**: Only expose specific tools (whitelist approach)
- **Exclude filters**: Hide specific tools (blacklist approach)
- **Combined filters**: Use both include and exclude lists together

### CLI Examples

```bash
# Only expose read and write operations from a filesystem server
llm mcp add filesystem \
  --transport stdio \
  --command python \
  --args -m \
  --args mcp.server.filesystem \
  --args /safe/directory \
  --tool-include read_file \
  --tool-include write_file \
  --tool-exclude delete_file

# Exclude dangerous administrative tools
llm mcp add api-server \
  --transport http \
  --url http://localhost:8000/mcp \
  --tool-exclude admin_reset \
  --tool-exclude clear_database \
  --tool-exclude delete_all
```

### Configuration File

Tool filters are also saved in the configuration file:

```json
{
  "servers": {
    "safe-filesystem": {
      "transport": "stdio",
      "command": "python",
      "args": ["-m", "mcp.server.filesystem", "/safe/dir"],
      "tool_filter_include": ["read_file", "write_file"],
      "tool_filter_exclude": ["delete_file"]
    }
  }
}
```

## Supported MCP Servers

This plugin works with any MCP server that follows the [Model Context Protocol specification](https://spec.modelcontextprotocol.io/). Some examples:

- [Toggl Track MCP](https://github.com/fuzzylabs/toggl-track-mcp) - Time tracking integration
- [Filesystem MCP](https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem) - File system operations
- [Git MCP](https://github.com/modelcontextprotocol/servers/tree/main/src/git) - Git repository management
- [SQLite MCP](https://github.com/modelcontextprotocol/servers/tree/main/src/sqlite) - Database operations

## License

MIT License. See [LICENSE](LICENSE) for details.

## Contributing

Contributions welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.
