"""Agent transkrypcji – konwersja audio na tekst przez OpenAI Whisper."""

import io
import re

from openai import AsyncOpenAI

from backend.config import settings
from backend.graph.state import NotebookState

# Wzorzec do wycinania hasła aktywującego z transkrypcji.
# Whisper transkrybuje całe nagranie – łącznie z hasłem "Notatnik, zapisz".
# Usuwamy je, żeby agent dostał tylko treść notatki.
_STRIP_WAKE_PATTERN = re.compile(
    r"^\s*notatni[ku]+[,.]?\s*(zapisz|powiedz)[,.]?\s*",
    flags=re.IGNORECASE,
)


async def transcribe_audio(state: NotebookState) -> dict:
    """
    Węzeł LangGraph: transkrybuj audio za pomocą Whisper API.

    Whisper transkrybuje pełne nagranie – od hasła aktywującego po koniec notatki.
    Po transkrypcji automatycznie wycinamy hasło ("Notatnik, zapisz" / "Notatnik, powiedz")
    aby agent intencji i kategoryzacji otrzymał wyłącznie treść notatki.

    Wejście:  state.audio_data (bytes WebM/WAV/MP3)
    Wyjście:  state.transcription (str, bez hasła aktywującego)
    """
    if not state.audio_data:
        return {"error": "Brak danych audio do transkrypcji."}

    try:
        client = AsyncOpenAI(api_key=settings.openai_api_key, timeout=30.0)

        audio_file = io.BytesIO(state.audio_data)
        audio_file.name = "audio.webm"

        response = await client.audio.transcriptions.create(
            model=settings.whisper_model,
            file=audio_file,
            language="pl",
            response_format="text",
        )

        raw = str(response).strip()

        # Usuń hasło aktywujące z początku transkrypcji
        cleaned = _STRIP_WAKE_PATTERN.sub("", raw).strip()

        # Jeśli po wycięciu nic nie zostało – zwróć oryginał (bezpieczeństwo)
        transcription = cleaned if len(cleaned) > 3 else raw

        return {"transcription": transcription, "error": None}

    except Exception as e:
        return {"error": f"Błąd transkrypcji: {e}"}
