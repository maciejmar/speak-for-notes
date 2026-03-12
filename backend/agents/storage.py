"""Agent zapisu – persystuje notatkę przez narzędzie MCP save_note."""

import re

from backend.agents.tools_registry import get_tool
from backend.graph.state import NotebookState


async def save_note_node(state: NotebookState) -> dict:
    """
    Węzeł LangGraph: zapisz notatkę do JSON i Qdrant przez MCP.

    Wejście:  state.note_category, state.note_content, state.transcription,
              state.enrichment
    Wyjście:  state.saved_id, state.response_text (potwierdzenie)
    """
    if state.error:
        return {}

    try:
        save_tool = get_tool("save_note")
        if not save_tool:
            return {"error": "Narzędzie save_note niedostępne."}

        result: str = await save_tool.ainvoke(
            {
                "category": state.note_category or "general",
                "content": state.note_content or state.transcription or "",
                "raw_transcription": state.transcription or "",
                "enrichment": state.enrichment or "",
            }
        )

        # Wyekstrahuj ID z odpowiedzi (format: "ID: xxxxxxxx")
        match = re.search(r"ID:\s*([a-f0-9]+)", result)
        note_id = match.group(1) if match else ""

        return {
            "saved_id": note_id,
            "response_text": result,
        }

    except Exception as e:
        return {"error": f"Błąd zapisu: {e}"}
