"""
Agent intencji – klasyfikuje transkrypcję i wyciąga szczegóły kalendarza.

Możliwe intencje:
  save_note    – użytkownik chce zapisać notatkę
  add_calendar – użytkownik chce dodać wydarzenie do kalendarza
  respond      – użytkownik zadaje pytanie (Notatnik, powiedz...)
  unknown      – niejasne polecenie
"""

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage

from backend.config import settings
from backend.graph.state import IntentResult, NotebookState

_SYSTEM_PROMPT = """Jesteś asystentem klasyfikującym polecenia głosowe w języku polskim.

Analizuj transkrypcję i zwróć JSON zgodny ze schematem:
{
  "intent": "save_note" | "add_calendar" | "respond" | "unknown",
  "calendar_title": "",
  "calendar_date": "",
  "calendar_time": "",
  "calendar_location": "",
  "calendar_description": "",
  "reasoning": ""
}

Zasady:
- "save_note": użytkownik podaje adres, myśl, zadanie, obserwację do zapisania
- "add_calendar": mención o spotkaniu, wydarzeniu, terminie (np. „jutro o 15", „w środę meeting")
- "respond": pytanie lub prośba o informację (zaczyna się od „powiedz", „co to", „wyjaśnij", „dlaczego" itp.)
- "unknown": niejasne lub brak sensownej treści

Dla "add_calendar" wyekstrahuj dostępne pola kalendarza.
Data powinna być w formacie YYYY-MM-DD jeśli możliwa, inaczej jako opis słowny.
Zwróć TYLKO JSON, bez komentarzy."""


async def classify_intent(state: NotebookState) -> dict:
    """
    Węzeł LangGraph: klasyfikuj intencję użytkownika.

    Wejście:  state.transcription
    Wyjście:  state.intent + pola kalendarza
    """
    if state.error:
        return {}

    if not state.transcription:
        return {"intent": "unknown"}

    # Jeśli użytkownik użył hasła "Notatnik, powiedz" → od razu respond
    if state.wake_word_type == "respond":
        return {"intent": "respond"}

    try:
        llm = ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=0,
        ).with_structured_output(IntentResult)

        messages = [
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content=f"Transkrypcja: {state.transcription}"),
        ]

        result: IntentResult = await llm.ainvoke(messages)

        return {
            "intent": result.intent,
            "calendar_title": result.calendar_title,
            "calendar_date": result.calendar_date,
            "calendar_time": result.calendar_time,
            "calendar_location": result.calendar_location,
            "calendar_description": result.calendar_description,
        }

    except Exception as e:
        return {"intent": "unknown", "error": f"Błąd klasyfikacji: {e}"}


def route_intent(state: NotebookState) -> str:
    """Warunkowe krawędzie grafu – routing według intencji."""
    if state.error:
        return "respond"
    return state.intent or "unknown"
