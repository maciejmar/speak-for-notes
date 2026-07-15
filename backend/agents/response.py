"""
Agent odpowiedzi – generuje odpowiedź głosową z kontekstem RAG.

Dla intent=respond:   RAG → Claude → TTS
Dla save/calendar:    potwierdzenie z TTS
"""

import io

from gtts import gTTS
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage

from backend.agents.ollama_utils import get_ollama_model
from backend.config import settings
from backend.graph.state import NotebookState
from backend.rag.retriever import get_rag_context

_RESPOND_SYSTEM = """Jesteś inteligentnym asystentem głosowym „Notatnik". Rozmawiasz
po polsku. Masz dostęp do notatek użytkownika i odpowiadasz na jego pytania.

Zasady:
- Odpowiedzi powinny być zwięzłe (2–4 zdania), klarowne, przydatne
- Jeśli odpowiedź pochodzi z notatek, wspomnij o tym naturalnie
- Mów w pierwszej osobie jako asystent
- Unikaj technicznego żargonu"""


async def generate_response(state: NotebookState) -> dict:
    """
    Węzeł LangGraph: wygeneruj odpowiedź tekstową.

    - Dla intent=respond: używa RAG do pobrania kontekstu z Qdrant
    - Dla save_note/add_calendar: zwraca istniejące potwierdzenie
    """
    # Potwierdzenie zapisu – response_text już ustawiony przez poprzedni węzeł
    if state.intent in ("save_note", "add_calendar") and state.response_text:
        return {}

    if state.error:
        return {
            "response_text": (
                f"Przepraszam, wystąpił błąd: {state.error}. "
                "Spróbuj ponownie."
            )
        }

    if not state.transcription:
        return {"response_text": "Nie rozumiem, powtórz proszę."}

    try:
        # RAG – pobierz powiązane notatki
        rag_context = await get_rag_context(state.transcription, k=4)

        llm = ChatOllama(
            model=await get_ollama_model(),
            base_url=settings.ollama_base_url,
            temperature=0.7,
        )

        system_msg = SystemMessage(
            content=f"{_RESPOND_SYSTEM}\n\n"
            f"Twoje notatki użytkownika (kontekst RAG):\n{rag_context}"
        )

        # Dodaj historię rozmowy
        history = list(state.messages[-6:]) if state.messages else []

        messages = [system_msg, *history, HumanMessage(content=state.transcription)]
        response = await llm.ainvoke(messages)

        return {"response_text": response.content.strip()}

    except Exception as e:
        return {"response_text": f"Przepraszam, nie mogę teraz odpowiedzieć. ({e})"}


async def text_to_speech(state: NotebookState) -> dict:
    """
    Węzeł LangGraph: konwertuj response_text na audio MP3 (gTTS).

    Wejście:  state.response_text
    Wyjście:  state.tts_audio (bytes MP3)
    """
    text = state.response_text
    if not text:
        return {}

    try:
        tts = gTTS(text=text, lang="pl", slow=False)
        buffer = io.BytesIO()
        tts.write_to_fp(buffer)
        buffer.seek(0)
        return {"tts_audio": buffer.read()}

    except Exception as e:
        return {"error": f"Błąd TTS: {e}"}
