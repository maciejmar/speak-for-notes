"""
MCP Server – Notatnik Głosowy.

Uruchamiaj jako subprocess przez LangGraph (stdio transport):
    python -m backend.mcp.server
"""

import sys
from pathlib import Path

# Upewnij się, że root projektu jest w PATH
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from mcp.server.fastmcp import FastMCP

from backend.mcp.tools.calendar_tool import add_calendar_event, get_calendar_events
from backend.mcp.tools.notes_tool import (
    get_notes,
    list_categories,
    save_note,
    search_notes_semantic,
)
from backend.mcp.tools.search_tool import web_search

mcp = FastMCP(
    "Notatnik Głosowy MCP",
    instructions=(
        "Serwer MCP dla inteligentnego notatnika głosowego. "
        "Udostępnia narzędzia do zarządzania notatkami, kalendarzem i wyszukiwaniem."
    ),
)

# ── Narzędzia notatnika ──────────────────────────────────────────────────────

mcp.tool()(save_note)
mcp.tool()(search_notes_semantic)
mcp.tool()(get_notes)
mcp.tool()(list_categories)

# ── Narzędzia kalendarza ─────────────────────────────────────────────────────

mcp.tool()(add_calendar_event)
mcp.tool()(get_calendar_events)

# ── Narzędzia wyszukiwania ───────────────────────────────────────────────────

mcp.tool()(web_search)

# ── Uruchomienie ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
