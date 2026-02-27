import json
import asyncio
import os
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional
from contextlib import AsyncExitStack

from langchain_core.tools import tool
import src.tools.base as base

# Import the actual MCP adapter
try:
    from langchain_mcp_adapters.tools import load_mcp_tools as adapter_load_mcp_tools
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    HAS_MCP = True
except ImportError:
    HAS_MCP = False
    print("Warning: langchain-mcp-adapters or mcp not installed. MCP tools will not be loaded.")

class MCPManager:
    """
    Manages MCP connections and tools.
    """
    _instance = None
    _exit_stack = None
    _tools = []

    @classmethod
    async def initialize(cls):
        """
        Initialize connections to all configured MCP servers.
        This must be called within an async context (e.g., startup).
        """
        if not HAS_MCP:
            return []

        if cls._exit_stack:
            # Already initialized
            return cls._tools

        cls._exit_stack = AsyncExitStack()
        cls._tools = []

        config_path = base.PROJECT_ROOT / "sf_mcp_config.json"
        if not config_path.exists():
            return []

        try:
            config_content = config_path.read_text(encoding="utf-8")
            config = json.loads(config_content)
            mcp_servers = config.get("mcpServers", {})

            print(f"[MCP] Found configuration for: {list(mcp_servers.keys())}")

            for name, settings in mcp_servers.items():
                command = settings.get("command")
                args = settings.get("args", [])
                env_config = settings.get("env", {})

                # Check if command exists
                if command == "uvx" and not shutil.which("uvx"):
                     # Fallback check or warning
                     pass

                # Resolve env vars in args (e.g. env:GITLAB_TOKEN)
                resolved_args = []

                # Merge current env with config env
                env = os.environ.copy()
                if env_config:
                    env.update(env_config)

                for arg in args:
                    if arg.startswith("env:"):
                        env_var = arg.split(":", 1)[1]
                        val = os.getenv(env_var)
                        if val:
                            resolved_args.append(val)
                        else:
                            print(f"[MCP] Warning: Environment variable {env_var} not found for server {name}")
                            resolved_args.append(arg) # Keep as is or skip? usually fail.
                    else:
                        resolved_args.append(arg)

                server_params = StdioServerParameters(
                    command=command,
                    args=resolved_args,
                    env=env
                )

                try:
                    # Connect to server
                    # We enter the context manager and keep it alive via ExitStack
                    read, write = await cls._exit_stack.enter_async_context(stdio_client(server_params))
                    session = await cls._exit_stack.enter_async_context(ClientSession(read, write))
                    await session.initialize()

                    # Load tools from this session
                    tools = await adapter_load_mcp_tools(session)
                    print(f"[MCP] Loaded {len(tools)} tools from {name}")
                    cls._tools.extend(tools)

                except Exception as e:
                    print(f"[MCP] Failed to connect to {name}: {e}")

        except Exception as e:
            print(f"[MCP] Error initializing: {e}")

        return cls._tools

    @classmethod
    async def cleanup(cls):
        """
        Close all connections.
        """
        if cls._exit_stack:
            await cls._exit_stack.aclose()
            cls._exit_stack = None
            cls._tools = []

    @classmethod
    def get_tools(cls) -> List[Any]:
        """
        Get the loaded tools.
        """
        return cls._tools

# Backward compatibility wrapper for sync usage (returns empty list if not init)
def load_mcp_tools() -> List[Any]:
    return MCPManager.get_tools()
