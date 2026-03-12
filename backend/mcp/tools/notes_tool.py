"""Narzędzia MCP do zarządzania notatkami – zapis do JSON + Qdrant."""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from openai import AsyncOpenAI
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from backend.config import settings

CATEGORIES = ["address", "thought", "task", "event", "general"]

CATEGORY_LABELS = {
    "address": "Adresy i kontakty",
    "thought": "Myśli do zapamiętania",
    "task": "Rzeczy do zrobienia",
    "event": "Wydarzenia",
    "general": "Ogólne",
}


def _load_notes() -> dict:
    if not settings.notes_file.exists():
        return {cat: [] for cat in CATEGORIES}
    return json.loads(settings.notes_file.read_text(encoding="utf-8"))


def _persist_notes(notes: dict) -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.notes_file.write_text(
        json.dumps(notes, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _qdrant() -> AsyncQdrantClient:
    return AsyncQdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)


async def _ensure_collection(client: AsyncQdrantClient) -> None:
    collections = await client.get_collections()
    names = [c.name for c in collections.collections]
    if settings.qdrant_collection not in names:
        await client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=VectorParams(
                size=settings.embedding_size, distance=Distance.COSINE
            ),
        )


async def _embed(text: str) -> list[float]:
    openai = AsyncOpenAI(api_key=settings.openai_api_key)
    response = await openai.embeddings.create(
        input=text, model=settings.embedding_model
    )
    return response.data[0].embedding


async def save_note(
    category: str,
    content: str,
    raw_transcription: str,
    enrichment: str = "",
) -> str:
    """
    Zapisz notatkę do bazy JSON i wektora Qdrant.

    Args:
        category: Kategoria notatki (address, thought, task, event, general).
        content: Przetworzona treść notatki.
        raw_transcription: Oryginalna transkrypcja głosu użytkownika.
        enrichment: Dodatkowe informacje wyszukane przez agenta badawczego.

    Returns:
        Potwierdzenie zapisu z ID notatki.
    """
    if category not in CATEGORIES:
        category = "general"

    note_id = str(uuid.uuid4())[:8]
    note = {
        "id": note_id,
        "created_at": datetime.now().isoformat(),
        "category": category,
        "content": content,
        "raw_transcription": raw_transcription,
        "enrichment": enrichment,
    }

    notes = _load_notes()
    notes[category].append(note)
    _persist_notes(notes)

    # Zapisz embedding do Qdrant
    try:
        text_to_embed = "\n".join(filter(None, [content, enrichment]))
        embedding = await _embed(text_to_embed)

        client = _qdrant()
        await _ensure_collection(client)
        await client.upsert(
            collection_name=settings.qdrant_collection,
            points=[
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=embedding,
                    payload={
                        "note_id": note_id,
                        "category": category,
                        "content": content,
                        "raw_transcription": raw_transcription,
                        "enrichment": enrichment,
                        "created_at": note["created_at"],
                    },
                )
            ],
        )
        await client.close()
    except Exception:
        pass  # Qdrant niedostępny – kontynuuj z JSON

    label = CATEGORY_LABELS.get(category, category)
    return f"✅ Notatka zapisana (ID: {note_id}) w kategorii '{label}'"


async def search_notes_semantic(
    query: str, limit: int = 5, category: str = ""
) -> str:
    """
    Wyszukaj notatki semantycznie przez Qdrant (RAG retrieval).

    Args:
        query: Zapytanie wyszukiwania w języku naturalnym.
        limit: Maksymalna liczba wyników (domyślnie 5).
        category: Ogranicz do kategorii (opcjonalnie).

    Returns:
        Dopasowane notatki z wynikami trafności.
    """
    try:
        query_embedding = await _embed(query)
        client = _qdrant()
        await _ensure_collection(client)

        search_filter = None
        if category and category in CATEGORIES:
            from qdrant_client.models import FieldCondition, Filter, MatchValue

            search_filter = Filter(
                must=[FieldCondition(key="category", match=MatchValue(value=category))]
            )

        results = await client.search(
            collection_name=settings.qdrant_collection,
            query_vector=query_embedding,
            limit=limit,
            query_filter=search_filter,
        )
        await client.close()

        if not results:
            return "Nie znaleziono pasujących notatek."

        formatted = []
        for r in results:
            p = r.payload
            label = CATEGORY_LABELS.get(p.get("category", ""), p.get("category", ""))
            enrichment_line = (
                f"\nDodatkowe info: {p['enrichment']}" if p.get("enrichment") else ""
            )
            formatted.append(
                f"[{label}] (trafność: {r.score:.2f})\n"
                f"Treść: {p['content']}"
                f"{enrichment_line}"
            )

        return "\n\n---\n\n".join(formatted)

    except Exception:
        # Fallback: przeszukiwanie słów kluczowych z JSON
        return _keyword_search(query, limit, category)


def _keyword_search(query: str, limit: int, category: str) -> str:
    notes = _load_notes()
    query_lower = query.lower()
    results: list[str] = []

    for cat, cat_notes in notes.items():
        if category and cat != category:
            continue
        for note in cat_notes:
            if query_lower in note.get("content", "").lower() or query_lower in note.get(
                "raw_transcription", ""
            ).lower():
                label = CATEGORY_LABELS.get(cat, cat)
                results.append(f"[{label}]\nTreść: {note['content']}")

    if not results:
        return "Nie znaleziono pasujących notatek."

    return "\n\n---\n\n".join(results[:limit])


def get_notes(category: str = "", limit: int = 20) -> str:
    """
    Pobierz notatki z bazy JSON, opcjonalnie filtruj według kategorii.

    Args:
        category: Kategoria do filtrowania (opcjonalnie).
        limit: Maksymalna liczba notatek na kategorię.

    Returns:
        Notatki w formacie JSON.
    """
    notes = _load_notes()

    if category and category in notes:
        result = {category: notes[category][-limit:]}
    else:
        result = {cat: notes_list[-limit:] for cat, notes_list in notes.items()}

    return json.dumps(result, ensure_ascii=False, indent=2)


def list_categories() -> str:
    """
    Zwróć listę kategorii z liczbą notatek w każdej.

    Returns:
        JSON z kategoriami i liczbami notatek.
    """
    notes = _load_notes()
    result = {
        CATEGORY_LABELS.get(cat, cat): len(lst) for cat, lst in notes.items()
    }
    return json.dumps(result, ensure_ascii=False)
