"""Definicja stanu grafu LangGraph dla notatnika głosowego."""

from typing import Annotated, Literal, Optional

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel


class NotebookState(BaseModel):
    """Stan grafu – przekazywany między węzłami agentów."""

    # ── Wejście ─────────────────────────────────────────────────────────────
    audio_data: Optional[bytes] = None
    wake_word_type: Literal["save", "respond"] = "save"

    # ── Transkrypcja ─────────────────────────────────────────────────────────
    transcription: Optional[str] = None

    # ── Klasyfikacja intencji ────────────────────────────────────────────────
    intent: Optional[Literal["save_note", "add_calendar", "respond", "unknown"]] = None

    # ── Szczegóły kalendarza (wyekstrahowane przez agenta intencji) ──────────
    calendar_title: str = ""
    calendar_date: str = ""
    calendar_time: str = ""
    calendar_location: str = ""
    calendar_description: str = ""

    # ── Notatka ──────────────────────────────────────────────────────────────
    note_category: Optional[
        Literal["address", "thought", "task", "event", "general"]
    ] = None
    note_content: Optional[str] = None  # Przetworzona treść
    enrichment: Optional[str] = None    # Wyniki badań agenta

    # ── Wyjście ──────────────────────────────────────────────────────────────
    response_text: Optional[str] = None
    tts_audio: Optional[bytes] = None
    saved_id: Optional[str] = None

    # ── Historia konwersacji (RAG + dialog) ──────────────────────────────────
    messages: Annotated[list[BaseMessage], add_messages] = []

    # ── Błędy ────────────────────────────────────────────────────────────────
    error: Optional[str] = None


class IntentResult(BaseModel):
    """Wynik klasyfikacji intencji przez LLM."""

    intent: Literal["save_note", "add_calendar", "respond", "unknown"]
    calendar_title: str = ""
    calendar_date: str = ""
    calendar_time: str = ""
    calendar_location: str = ""
    calendar_description: str = ""
    reasoning: str = ""


class CategoryResult(BaseModel):
    """Wynik kategoryzacji notatki przez LLM."""

    category: Literal["address", "thought", "task", "event", "general"]
    content: str  # Oczyszczona, sformatowana treść
    reasoning: str = ""
