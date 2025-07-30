#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "bespoken>=0.2.2",
#     "llm-anthropic",
#     "llm-mcp-plugin @ git+https://github.com/d-lowl/llm-mcp-plugin.git",
# ]
# ///
import os

from bespoken import chat, ui  # type: ignore[import-not-found]
from bespoken.tools import TodoTools  # type: ignore[import-not-found]

from llm_mcp_plugin.config import MCPServerConfig
from llm_mcp_plugin.mcp_toolbox import MCPToolbox

SYSTEM_PROMPT = """
You are a helpful assistant that can help with tasks in Notion.
"""

NOTION_API_KEY = os.getenv("NOTION_API_KEY")
if NOTION_API_KEY is None:
    raise ValueError("NOTION_API_KEY is not set")


def set_role() -> str:
    """Set a role for the assistant"""
    roles = ["developer", "teacher", "analyst", "creative writer", "code reviewer"]
    role = ui.choice("What role should I take?", roles)
    return f"You are now acting as a {role}. Please respond in character for this role."


def whoami() -> str:
    """Fetch the information about the user in Notion."""
    return "Who are you logged in as in Notion?"


mcp_toolbox = MCPToolbox(
    config=MCPServerConfig(
        name="notion",
        transport="stdio",
        command="npx",
        args=["-y", "@notionhq/notion-mcp-server"],
        env={"OPENAPI_MCP_HEADERS": f'{{"Authorization": "Bearer {NOTION_API_KEY}", "Notion-Version": "2022-06-28" }}'},
        url=None,
        timeout=30,
        description=None,
        stderr_mode="disable",
        stderr_file=None,
        stderr_append=False,
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
