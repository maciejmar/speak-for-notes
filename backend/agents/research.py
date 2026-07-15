"""
Agent badawczy – wzbogaca notatki kategorii „thought" informacjami z internetu.

Używa narzędzia MCP web_search do wyszukiwania informacji.
"""

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage

from backend.agents.ollama_utils import get_ollama_model, invoke_with_fallback
from backend.agents.tools_registry import get_tool
from backend.config import settings
from backend.graph.state import NotebookState

_SYSTEM_PROMPT = """Jesteś asystentem badawczym. Na podstawie wyników wyszukiwania
przygotuj zwięzłe (3-5 zdań) podsumowanie dotyczące tematu notatki.
Pisz po polsku. Skup się na najważniejszych faktach i kontekście.
Nie powtarzaj treści notatki – uzupełnij ją o nowe informacje."""


async def research_topic(state: NotebookState) -> dict:
    """
    Węzeł LangGraph: wyszukaj informacje o temacie myśli i wzbogać notatkę.

    Wejście:  state.note_content
    Wyjście:  state.enrichment
    """
    if state.error or not state.note_content:
        return {}

    try:
        search_tool = get_tool("web_search")
        if not search_tool:
            return {"enrichment": ""}

        # Przeszukaj internet
        search_results = await search_tool.ainvoke(
            {"query": state.note_content, "max_results": 3}
        )

        # Streść wyniki
        primary = ChatOllama(
            model=await get_ollama_model(),
            base_url=settings.ollama_base_url,
            temperature=0.3,
        )

        messages = [
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(
                content=(
                    f"Notatka użytkownika: {state.note_content}\n\n"
                    f"Wyniki wyszukiwania:\n{search_results}"
                )
            ),
        ]

        response = await invoke_with_fallback(
            primary, messages, temperature=0.3, agent_name="research"
        )
        enrichment = response.content.strip()

        return {"enrichment": enrichment}

    except Exception as e:
        return {"enrichment": "", "error": f"Błąd badań: {e}"}
