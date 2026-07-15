"""
Rejestr narzędzi MCP – singleton inicjalizowany przy starcie aplikacji.

LangGraph używa MultiServerMCPClient do uruchamiania serwera MCP
jako subprocess (transport stdio) i importowania narzędzi jako
LangChain tools.
"""

import sys
from typing import Any

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient

_mcp_client: MultiServerMCPClient | None = None
_tools: dict[str, BaseTool] = {}


def get_mcp_server_config() -> dict[str, Any]:
    return {
        "notebook": {
            "command": sys.executable,
            "args": ["-m", "backend.mcp.server"],
            "transport": "stdio",
            "env": None,
        }
    }


async def init_mcp_tools() -> MultiServerMCPClient:
    """Uruchom klient MCP i załaduj narzędzia. Wywołaj przy starcie FastAPI."""
    global _mcp_client, _tools

    _mcp_client = MultiServerMCPClient(get_mcp_server_config())
    tools_list: list[BaseTool] = await _mcp_client.get_tools()
    _tools = {tool.name: tool for tool in tools_list}

    return _mcp_client


async def close_mcp_client() -> None:
    """Wyczyść referencję klienta MCP przy zatrzymaniu aplikacji."""
    global _mcp_client, _tools
    _mcp_client = None
    _tools = {}


def get_tool(name: str) -> BaseTool | None:
    """Pobierz narzędzie MCP po nazwie."""
    return _tools.get(name)


def get_all_tools() -> list[BaseTool]:
    """Zwróć wszystkie załadowane narzędzia MCP."""
    return list(_tools.values())
