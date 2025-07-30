"""Tests for the configuration module."""

import json
import tempfile
from pathlib import Path

import pytest

from llm_mcp_plugin.config import MCPPluginConfig, MCPServerConfig


class TestMCPServerConfig:
    """Tests for MCPServerConfig."""

    def test_stdio_config_valid(self):
        """Test valid stdio configuration."""
        config = MCPServerConfig(
            name="test",
            transport="stdio",
            command="python",
            args=["-m", "test"],
            env={"VAR": "value"},
        )
        config.validate_config()  # Should not raise

    def test_stdio_config_missing_command(self):
        """Test stdio configuration missing command."""
        config = MCPServerConfig(name="test", transport="stdio")
        with pytest.raises(ValueError, match="Command is required"):
            config.validate_config()

    def test_http_config_valid(self):
        """Test valid HTTP configuration."""
        config = MCPServerConfig(
            name="test",
            transport="http",
            url="http://localhost:8000/mcp",
            headers={"Authorization": "Bearer token"},
        )
        config.validate_config()  # Should not raise

    def test_http_config_missing_url(self):
        """Test HTTP configuration missing URL."""
        config = MCPServerConfig(name="test", transport="http")
        with pytest.raises(ValueError, match="URL is required"):
            config.validate_config()

    def test_invalid_transport(self):
        """Test invalid transport type."""
        with pytest.raises(ValueError):
            MCPServerConfig(name="test", transport="invalid")


class TestMCPPluginConfig:
    """Tests for MCPPluginConfig."""

    def test_empty_config(self):
        """Test empty configuration."""
        config = MCPPluginConfig()
        assert config.servers == {}

    def test_add_server(self):
        """Test adding a server configuration."""
        config = MCPPluginConfig()
        server = MCPServerConfig(name="test", transport="stdio", command="python")

        config.add_server(server)
        assert "test" in config.servers
        assert config.servers["test"] == server

    def test_remove_server(self):
        """Test removing a server configuration."""
        config = MCPPluginConfig()
        server = MCPServerConfig(name="test", transport="stdio", command="python")

        config.add_server(server)
        assert config.remove_server("test") is True
        assert "test" not in config.servers
        assert config.remove_server("nonexistent") is False

    def test_get_server(self):
        """Test getting a server configuration."""
        config = MCPPluginConfig()
        server = MCPServerConfig(name="test", transport="stdio", command="python")

        config.add_server(server)
        retrieved = config.get_server("test")
        assert retrieved == server
        assert config.get_server("nonexistent") is None

    def test_save_and_load_config(self):
        """Test saving and loading configuration files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_config.json"

            # Create and save config
            config = MCPPluginConfig()
            server = MCPServerConfig(
                name="test",
                transport="stdio",
                command="python",
                args=["-m", "test"],
                env={"VAR": "value"},
                description="Test server",
            )
            config.add_server(server)
            config.save_to_file(config_path)

            # Load config
            loaded_config = MCPPluginConfig.load_from_file(config_path)

            assert "test" in loaded_config.servers
            loaded_server = loaded_config.servers["test"]
            assert loaded_server.name == "test"
            assert loaded_server.transport == "stdio"
            assert loaded_server.command == "python"
            assert loaded_server.args == ["-m", "test"]
            assert loaded_server.env == {"VAR": "value"}
            assert loaded_server.description == "Test server"

    def test_load_nonexistent_config(self):
        """Test loading a nonexistent configuration file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "nonexistent.json"
            config = MCPPluginConfig.load_from_file(config_path)
            assert config.servers == {}

    def test_load_invalid_json(self):
        """Test loading invalid JSON configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "invalid.json"

            # Write invalid JSON
            with open(config_path, "w") as f:
                f.write("{ invalid json }")

            with pytest.raises(ValueError, match="Failed to load config"):
                MCPPluginConfig.load_from_file(config_path)

    def test_config_json_format(self):
        """Test the expected JSON format for configuration."""
        config = MCPPluginConfig()

        # Add different types of servers
        stdio_server = MCPServerConfig(
            name="stdio_test",
            transport="stdio",
            command="python",
            args=["-m", "test"],
            env={"API_KEY": "secret"},
        )

        http_server = MCPServerConfig(
            name="http_test",
            transport="http",
            url="http://localhost:8000/mcp",
            headers={"Authorization": "Bearer token"},
        )

        config.add_server(stdio_server)
        config.add_server(http_server)

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "format_test.json"
            config.save_to_file(config_path)

            # Check the JSON structure
            with open(config_path, "r") as f:
                data = json.load(f)

            assert "servers" in data
            assert "stdio_test" in data["servers"]
            assert "http_test" in data["servers"]

            stdio_data = data["servers"]["stdio_test"]
            assert stdio_data["transport"] == "stdio"
            assert stdio_data["command"] == "python"
            assert stdio_data["args"] == ["-m", "test"]
            assert stdio_data["env"] == {"API_KEY": "secret"}

            http_data = data["servers"]["http_test"]
            assert http_data["transport"] == "http"
            assert http_data["url"] == "http://localhost:8000/mcp"
            assert http_data["headers"] == {"Authorization": "Bearer token"}
