"""
Graf LangGraph – orkiestrator notatnika głosowego.

Topologia:

  START
    │
  transcribe_audio
    │
  classify_intent
    │
  ┌─────────────────────────────────────────┐
  │         Routing wg intencji             │
  │  save_note ──► categorize_note          │
  │                    │                    │
  │             ┌──────┴──────┐             │
  │          thought        inne            │
  │             │              │            │
  │        research_topic  save_note_node   │
  │             │              │            │
  │        save_note_node ◄────┘            │
  │             │                           │
  │  add_calendar ──► add_to_calendar       │
  │                        │                │
  │  respond/unknown ────► generate_resp    │
  │                             │           │
  │                        text_to_speech   │
  └─────────────────────────────────────────┘
                               │
                              END
"""

from langgraph.graph import END, START, StateGraph

from backend.agents.calendar_agent import add_to_calendar
from backend.agents.categorization import categorize_note, route_category
from backend.agents.intent import classify_intent, route_intent
from backend.agents.research import research_topic
from backend.agents.response import generate_response, text_to_speech
from backend.agents.storage import save_note_node
from backend.agents.transcription import transcribe_audio
from backend.graph.state import NotebookState


def build_graph() -> StateGraph:
    """Zbuduj i skompiluj graf notatnika."""
    builder = StateGraph(NotebookState)

    # ── Węzły ────────────────────────────────────────────────────────────────
    builder.add_node("transcribe_audio", transcribe_audio)
    builder.add_node("classify_intent", classify_intent)
    builder.add_node("categorize_note", categorize_note)
    builder.add_node("research_topic", research_topic)
    builder.add_node("save_note_node", save_note_node)
    builder.add_node("add_to_calendar", add_to_calendar)
    builder.add_node("generate_response", generate_response)
    builder.add_node("text_to_speech", text_to_speech)

    # ── Krawędzie stałe ──────────────────────────────────────────────────────
    builder.add_edge(START, "transcribe_audio")
    builder.add_edge("transcribe_audio", "classify_intent")

    # ── Routing wg intencji ──────────────────────────────────────────────────
    builder.add_conditional_edges(
        "classify_intent",
        route_intent,
        {
            "save_note": "categorize_note",
            "add_calendar": "add_to_calendar",
            "respond": "generate_response",
            "unknown": "generate_response",
        },
    )

    # ── Routing wg kategorii ─────────────────────────────────────────────────
    builder.add_conditional_edges(
        "categorize_note",
        route_category,
        {
            "thought": "research_topic",   # Myśli → badania → zapis
            "address": "save_note_node",
            "task": "save_note_node",
            "event": "save_note_node",
            "general": "save_note_node",
        },
    )

    builder.add_edge("research_topic", "save_note_node")
    builder.add_edge("save_note_node", "generate_response")
    builder.add_edge("add_to_calendar", "generate_response")
    builder.add_edge("generate_response", "text_to_speech")
    builder.add_edge("text_to_speech", END)

    return builder.compile()


# Singleton – kompilowany raz przy imporcie modułu
notebook_graph = build_graph()
