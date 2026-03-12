"""
FastAPI – backend notatnika głosowego.

Endpointy:
  WebSocket  /ws                    – real-time audio ↔ odpowiedź
  GET        /api/notes             – pobierz notatki (JSON)
  GET        /api/notes/search      – semantyczne wyszukiwanie (RAG)
  GET        /api/calendar          – pobierz wydarzenia
  GET        /api/categories        – statystyki kategorii
  GET        /health                – status serwisu
  static     /                      – serwuje zbudowany Angular PWA (opcjonalnie)
"""

import asyncio
import base64
import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.agents.tools_registry import close_mcp_client, init_mcp_tools
from backend.config import settings
from backend.graph.notebook_graph import notebook_graph
from backend.graph.state import NotebookState
from backend.mcp.tools.calendar_tool import get_calendar_events
from backend.mcp.tools.notes_tool import get_notes, list_categories, search_notes_semantic

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ── Lifespan – inicjalizacja MCP ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Inicjalizuję klienta MCP...")
    try:
        await init_mcp_tools()
        logger.info("MCP gotowy.")
    except Exception as e:
        logger.warning(f"MCP niedostępny: {e} – kontynuuję bez narzędzi MCP.")
    yield
    await close_mcp_client()
    logger.info("MCP zamknięty.")


# ── Aplikacja ─────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Notatnik Głosowy API",
    description="Inteligentny asystent głosowy z LangGraph, MCP i Qdrant RAG",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── WebSocket ─────────────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    conversation_messages: list = []

    try:
        while True:
            raw = await websocket.receive_text()
            payload = json.loads(raw)

            msg_type = payload.get("type")

            # ── Przetwarzanie audio ──────────────────────────────────────────
            if msg_type == "audio":
                wake_word = payload.get("wake_word", "save")
                audio_b64 = payload.get("data", "")

                if not audio_b64:
                    await websocket.send_text(
                        json.dumps({"type": "error", "message": "Brak danych audio."})
                    )
                    continue

                audio_bytes = base64.b64decode(audio_b64)

                # Statusy pośrednie
                await _send_status(websocket, "Transkrybuję nagranie...")

                # Uruchom graf LangGraph
                initial_state = NotebookState(
                    audio_data=audio_bytes,
                    wake_word_type=wake_word,
                    messages=conversation_messages,
                )

                try:
                    final_state: NotebookState = await asyncio.wait_for(
                        notebook_graph.ainvoke(initial_state),
                        timeout=60.0,
                    )
                except asyncio.TimeoutError:
                    logger.error("Graf przekroczył limit czasu 60s.")
                    await websocket.send_text(
                        json.dumps({"type": "error", "message": "Przekroczono limit czasu przetwarzania (60s). Spróbuj ponownie."})
                    )
                    continue
                except Exception as e:
                    logger.error(f"Błąd grafu: {e}", exc_info=True)
                    await websocket.send_text(
                        json.dumps({"type": "error", "message": str(e)})
                    )
                    continue

                # LangGraph zwraca dict (AddableValuesDict), nie obiekt NotebookState
                fs = final_state if isinstance(final_state, dict) else final_state.__dict__

                # Zaktualizuj historię konwersacji
                conversation_messages = list(fs.get("messages", []))

                # Odpowiedź
                tts_audio = fs.get("tts_audio")
                result = {
                    "type": "result",
                    "transcription": fs.get("transcription"),
                    "intent": fs.get("intent"),
                    "category": fs.get("note_category"),
                    "response_text": fs.get("response_text"),
                    "saved_id": fs.get("saved_id"),
                    "enrichment": fs.get("enrichment"),
                    "audio": base64.b64encode(tts_audio).decode() if tts_audio else None,
                    "error": fs.get("error"),
                }
                await websocket.send_text(json.dumps(result))

            # ── Reset konwersacji ────────────────────────────────────────────
            elif msg_type == "reset":
                conversation_messages = []
                await websocket.send_text(
                    json.dumps({"type": "status", "message": "Rozmowa zresetowana."})
                )

            else:
                await websocket.send_text(
                    json.dumps({"type": "error", "message": f"Nieznany typ: {msg_type}"})
                )

    except WebSocketDisconnect:
        logger.info("Klient WebSocket rozłączony.")
    except Exception as e:
        logger.error(f"Błąd WebSocket: {e}", exc_info=True)


async def _send_status(websocket: WebSocket, message: str) -> None:
    await websocket.send_text(json.dumps({"type": "status", "message": message}))


# ── REST API ──────────────────────────────────────────────────────────────────

@app.get("/api/notes")
async def api_get_notes(
    category: str = Query("", description="Filtruj według kategorii"),
    limit: int = Query(20, ge=1, le=100),
):
    """Pobierz notatki z JSON (paginacja, filtrowanie)."""
    raw = get_notes(category=category, limit=limit)
    return json.loads(raw)


@app.get("/api/notes/search")
async def api_search_notes(
    q: str = Query(..., description="Zapytanie semantyczne (RAG)"),
    category: str = Query("", description="Filtruj według kategorii"),
    limit: int = Query(5, ge=1, le=20),
):
    """Semantyczne wyszukiwanie notatek przez Qdrant (RAG)."""
    result = await search_notes_semantic(query=q, limit=limit, category=category)
    return {"query": q, "results": result}


@app.get("/api/calendar")
async def api_get_calendar(
    date_from: str = Query("", description="Data od YYYY-MM-DD"),
    date_to: str = Query("", description="Data do YYYY-MM-DD"),
):
    """Pobierz wydarzenia kalendarza."""
    raw = get_calendar_events(date_from=date_from, date_to=date_to)
    return json.loads(raw)


@app.get("/api/categories")
async def api_get_categories():
    """Statystyki kategorii notatek."""
    raw = list_categories()
    return json.loads(raw)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "qdrant_host": settings.qdrant_host,
        "qdrant_port": settings.qdrant_port,
        "model": settings.claude_model,
    }


# ── Serwowanie Angular PWA (production build) ────────────────────────────────
# Montowane na końcu żeby nie nadpisywać /api/* endpointów.
# Używaj tego zamiast osobnego ng serve gdy chcesz wszystko na jednym porcie.
_ANGULAR_DIST = Path(__file__).parents[1] / "frontend" / "dist" / "speak-for-notes" / "browser"

if _ANGULAR_DIST.exists():
    # manifest.webmanifest wymaga poprawnego MIME type
    @app.get("/manifest.webmanifest")
    async def manifest():
        return FileResponse(
            _ANGULAR_DIST / "manifest.webmanifest",
            media_type="application/manifest+json",
        )

    # Service Worker musi być serwowany z root scope
    @app.get("/ngsw-worker.js")
    async def ngsw_worker():
        return FileResponse(
            _ANGULAR_DIST / "ngsw-worker.js",
            media_type="application/javascript",
            headers={"Service-Worker-Allowed": "/"},
        )

    # Statyczne pliki Angular
    app.mount("/", StaticFiles(directory=str(_ANGULAR_DIST), html=True), name="angular")
