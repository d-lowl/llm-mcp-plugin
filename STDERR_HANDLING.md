# STDERR Handling for MCP Servers

This document describes the STDERR handling functionality that allows you to control how standard error output from MCP servers is managed.

## Overview

When running MCP servers in stdio mode, the server process may write error messages, debug information, or other diagnostic output to STDERR. By default, this output is displayed directly in the terminal, which can be disruptive or unwanted. The STDERR handling feature provides three options for managing this output:

1. **Disable** - Silence STDERR completely (default)
2. **File** - Redirect STDERR to a specified file
3. **Terminal** - Display STDERR in the terminal (original behavior)

## Configuration Options

The following new configuration options are available in `MCPServerConfig`:

### `stderr_mode`
- **Type**: `"disable" | "file" | "terminal"`
- **Default**: `"disable"`
- **Description**: How to handle STDERR output from the MCP server

### `stderr_file`
- **Type**: `string | null`
- **Default**: `null`
- **Description**: File path to redirect STDERR to (only used when `stderr_mode="file"`)

### `stderr_append`
- **Type**: `boolean`
- **Default**: `false`
- **Description**: Whether to append to the stderr file (true) or overwrite it (false)

## Usage Examples

### 1. Disable STDERR (Default)

```json
{
  "servers": {
    "my-server": {
      "transport": "stdio",
      "command": "python",
      "args": ["/path/to/server.py"],
      "stderr_mode": "disable"
    }
  }
}
```

This is the default behavior. All STDERR output from the server is discarded.

### 2. Redirect STDERR to File

```json
{
  "servers": {
    "my-server": {
      "transport": "stdio",
      "command": "python",
      "args": ["/path/to/server.py"],
      "stderr_mode": "file",
      "stderr_file": "~/.logs/mcp_server_errors.log",
      "stderr_append": true
    }
  }
}
```

This redirects all STDERR output to the specified file. The file will be created if it doesn't exist, including any necessary parent directories.

### 3. Display STDERR in Terminal

```json
{
  "servers": {
    "my-server": {
      "transport": "stdio",
      "command": "python",
      "args": ["/path/to/server.py"],
      "stderr_mode": "terminal"
    }
  }
}
```

This displays STDERR output in the terminal, which is useful for debugging.

## Programmatic Usage

You can also configure STDERR handling programmatically:

```python
from llm_mcp_plugin.config import MCPServerConfig
from llm_mcp_plugin.mcp_client import MCPClient

# Configure server with STDERR to file
config = MCPServerConfig(
    name="my-server",
    transport="stdio",
    command="python",
    args=["/path/to/server.py"],
    stderr_mode="file",
    stderr_file="/tmp/mcp_debug.log",
    stderr_append=False
)

client = MCPClient(config)

# Use the client normally - STDERR will be handled according to config
async with client.connect() as session:
    tools = await session.list_tools()
    # ... use the tools
```

## Implementation Details

### File Handling
- When `stderr_mode="file"`, the specified file path is expanded (e.g., `~` becomes the home directory)
- Parent directories are created automatically if they don't exist
- The file is opened in append mode if `stderr_append=true`, otherwise in write mode (overwrite)
- File handles are properly closed when the connection ends

### Error Handling
- If the stderr file cannot be opened (e.g., permission denied), STDERR is automatically disabled
- Invalid `stderr_mode` values default to "disable" with a warning
- Configuration validation ensures `stderr_file` is provided when `stderr_mode="file"`

### Transport Support
- STDERR handling only applies to stdio transport
- SSE and HTTP transports are not affected by these settings

## Common Use Cases

### Development and Debugging
```json
{
  "stderr_mode": "terminal",
  "description": "See all debug output in terminal"
}
```

### Production Logging
```json
{
  "stderr_mode": "file",
  "stderr_file": "/var/log/mcp/server.log",
  "stderr_append": true,
  "description": "Log errors for monitoring"
}
```

### Clean Operation
```json
{
  "stderr_mode": "disable",
  "description": "Silent operation (default)"
}
```

### Per-Session Debugging
```json
{
  "stderr_mode": "file",
  "stderr_file": "/tmp/mcp_debug_session.log",
  "stderr_append": false,
  "description": "Fresh log file for each session"
}
```

## Testing

A test script is provided in `test_stderr_handling.py` that demonstrates all three modes:

```bash
python test_stderr_handling.py
```

This script creates temporary MCP servers that write to STDERR and verifies that the output is handled correctly according to the configuration.

## Troubleshooting

### STDERR file not created
- Check file permissions for the target directory
- Ensure the parent directory exists or can be created
- Verify the file path is valid

### Permission denied errors
- Make sure the process has write permissions to the target directory
- Consider using a different location like `/tmp/` for testing

### STDERR still appearing in terminal
- Verify `stderr_mode` is set correctly
- Check that the configuration is being loaded properly
- Ensure you're not seeing STDOUT output instead of STDERR

## Migration from Previous Versions

If you're upgrading from a previous version:

1. The default behavior is now to disable STDERR (previously it was shown in terminal)
2. To maintain the old behavior, set `stderr_mode: "terminal"`
3. Existing configurations without STDERR settings will use the new default (disable)

## Limitations

- Only available for stdio transport
- File path expansion is basic (only `~` is supported)
- No log rotation or size limits are implemented
- STDERR and STDOUT cannot be combined into a single file
