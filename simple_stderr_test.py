#!/usr/bin/env python3
"""Simple test to verify STDERR handling configuration works."""

import os
import sys
import tempfile
from pathlib import Path

# Add the project to path
sys.path.insert(0, str(Path(__file__).parent))

from llm_mcp_plugin.config import MCPServerConfig


def test_config_validation():
    """Test that STDERR configuration validation works."""
    print("Testing configuration validation...")
    
    # Test basic config works
    try:
        config = MCPServerConfig(
            name="test",
            transport="stdio",
            command="python",
            args=["test.py"],
            stderr_mode="disable"
        )
        config.validate_config()
        print("✓ Basic config validation works")
    except Exception as e:
        print(f"✗ Basic config failed: {e}")
        return False
    
    # Test file mode without stderr_file fails
    try:
        config2 = MCPServerConfig(
            name="test2", 
            transport="stdio",
            command="python",
            args=["test.py"],
            stderr_mode="file"
            # Missing stderr_file
        )
        config2.validate_config()
        print("✗ Should have failed validation - missing stderr_file")
        return False
    except ValueError as e:
        print(f"✓ Validation correctly failed: {e}")
    except Exception as e:
        print(f"✗ Wrong exception type: {e}")
        return False
    
    # Test valid file mode works
    try:
        config3 = MCPServerConfig(
            name="test3",
            transport="stdio", 
            command="python",
            args=["test.py"],
            stderr_mode="file",
            stderr_file="/tmp/test.log"
        )
        config3.validate_config()
        print("✓ Valid file config works")
    except Exception as e:
        print(f"✗ Valid config failed: {e}")
        return False
    
    return True


def test_stderr_file_handling():
    """Test that STDERR file objects can be created."""
    print("\nTesting STDERR file handling...")
    
    # Import here to avoid issues if other parts fail
    from llm_mcp_plugin.mcp_client import MCPClient
    
    # Test disable mode
    config = MCPServerConfig(
        name="test-disable",
        transport="stdio",
        command="echo", 
        args=["test"],
        stderr_mode="disable"
    )
    
    client = MCPClient(config)
    stderr_target = client._get_stderr_target()
    
    try:
        # Should be able to write to it
        stderr_target.write("test\n")
        stderr_target.flush()
        print("✓ Disable mode stderr target works")
    except Exception as e:
        print(f"✗ Disable mode failed: {e}")
        return False
    finally:
        if stderr_target != sys.stderr:
            stderr_target.close()
    
    # Test file mode
    with tempfile.NamedTemporaryFile(delete=False) as f:
        stderr_file = f.name
    
    try:
        config2 = MCPServerConfig(
            name="test-file",
            transport="stdio",
            command="echo",
            args=["test"], 
            stderr_mode="file",
            stderr_file=stderr_file,
            stderr_append=False
        )
        
        client2 = MCPClient(config2)
        stderr_target2 = client2._get_stderr_target()
        
        # Should be able to write to file
        stderr_target2.write("test stderr content\n")
        stderr_target2.flush()
        stderr_target2.close()
        
        # Check file was written
        if os.path.exists(stderr_file):
            with open(stderr_file, 'r') as f:
                content = f.read()
            if "test stderr content" in content:
                print("✓ File mode stderr target works")
            else:
                print(f"✗ File content incorrect: {content}")
                return False
        else:
            print("✗ Stderr file was not created")
            return False
            
    except Exception as e:
        print(f"✗ File mode failed: {e}")
        return False
    finally:
        if os.path.exists(stderr_file):
            os.unlink(stderr_file)
    
    # Test terminal mode
    config3 = MCPServerConfig(
        name="test-terminal",
        transport="stdio",
        command="echo",
        args=["test"],
        stderr_mode="terminal"
    )
    
    client3 = MCPClient(config3)
    stderr_target3 = client3._get_stderr_target()
    
    if stderr_target3 == sys.stderr:
        print("✓ Terminal mode stderr target works")
    else:
        print("✗ Terminal mode should return sys.stderr")
        return False
    
    return True


def main():
    """Run all tests."""
    print("=" * 50)
    print("MCP STDERR Handling Configuration Tests")
    print("=" * 50)
    
    success = True
    
    success &= test_config_validation()
    success &= test_stderr_file_handling()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ All tests passed!")
        return 0
    else:
        print("❌ Some tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())