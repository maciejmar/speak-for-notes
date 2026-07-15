"""
Agent kategoryzacji – przypisuje notatkę do odpowiedniej kategorii
i oczyszcza treść.

Kategorie:
  address  – adres, kontakt, lokalizacja
  thought  – myśl, idea, obserwacja do przemyślenia
  task     – zadanie do zrobienia (TODO)
  event    – wydarzenie, wspomnienie, historia
  general  – nie pasuje do innych kategorii
"""

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage

from backend.agents.ollama_utils import get_fallback_llm, get_ollama_model
from backend.config import settings
from backend.graph.state import CategoryResult, NotebookState

_SYSTEM_PROMPT = """Jesteś asystentem kategoryzującym notatki głosowe w języku polskim.

Analizuj treść i zwróć JSON:
{
  "category": "address" | "thought" | "task" | "event" | "general",
  "content": "<oczyszczona, sformatowana treść notatki>",
  "reasoning": "<krótkie uzasadnienie>"
}

Zasady kategoryzacji:
- "address": ulica, numer domu, miasto, numer telefonu, email, strona www
- "thought": idea, myśl filozoficzna, obserwacja, coś do przemyślenia
- "task": coś co trzeba zrobić, kupić, załatwić, zadzwonić
- "event": coś co się stało lub wydarzy, spotkanie zapisane bez daty
- "general": wszystko inne

Dla "content": usuń słowa-zainicjatora (np. "zapisz", "notatka"), popraw
interpunkcję i sformatuj jako zwięzłą notatkę.

Zwróć TYLKO JSON."""


async def categorize_note(state: NotebookState) -> dict:
    """
    Węzeł LangGraph: kategoryzuj notatkę i oczyść treść.

    Wejście:  state.transcription
    Wyjście:  state.note_category, state.note_content
    """
    if state.error:
        return {}

    try:
        primary = ChatOllama(
            model=await get_ollama_model(),
            base_url=settings.ollama_base_url,
            temperature=0,
        ).with_structured_output(CategoryResult, method="json_schema")
        fallback = get_fallback_llm().with_structured_output(CategoryResult)
        llm = primary.with_fallbacks([fallback])

        messages = [
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content=f"Treść do skategoryzowania: {state.transcription}"),
        ]

        result: CategoryResult = await llm.ainvoke(messages)

        return {
            "note_category": result.category,
            "note_content": result.content,
        }

    except Exception as e:
        return {
            "note_category": "general",
            "note_content": state.transcription,
            "error": f"Błąd kategoryzacji: {e}",
        }


def route_category(state: NotebookState) -> str:
    """Routing po kategoryzacji – myśli trafiają do badań."""
    return state.note_category or "general"
