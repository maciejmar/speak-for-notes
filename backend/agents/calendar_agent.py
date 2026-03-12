"""Agent kalendarza – dodaje wydarzenie przez narzędzie MCP add_calendar_event."""

from backend.agents.tools_registry import get_tool
from backend.graph.state import NotebookState


async def add_to_calendar(state: NotebookState) -> dict:
    """
    Węzeł LangGraph: dodaj wydarzenie do kalendarza przez MCP.

    Wejście:  state.calendar_title, state.calendar_date, state.calendar_time,
              state.calendar_location, state.calendar_description
    Wyjście:  state.saved_id, state.response_text (potwierdzenie)
    """
    if state.error:
        return {}

    try:
        calendar_tool = get_tool("add_calendar_event")
        if not calendar_tool:
            return {"error": "Narzędzie add_calendar_event niedostępne."}

        title = state.calendar_title or state.transcription or "Wydarzenie"
        date = state.calendar_date or "do ustalenia"

        result: str = await calendar_tool.ainvoke(
            {
                "title": title,
                "date": date,
                "time": state.calendar_time or "",
                "description": state.calendar_description or state.transcription or "",
                "location": state.calendar_location or "",
            }
        )

        return {
            "saved_id": "",
            "response_text": result,
        }

    except Exception as e:
        return {"error": f"Błąd kalendarza: {e}"}
