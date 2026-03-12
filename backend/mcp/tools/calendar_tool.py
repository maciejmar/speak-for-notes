"""Narzędzia MCP do zarządzania kalendarzem."""

import json
import uuid
from datetime import datetime

from backend.config import settings


def _load_events() -> list:
    if not settings.calendar_file.exists():
        return []
    return json.loads(settings.calendar_file.read_text(encoding="utf-8"))


def _persist_events(events: list) -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.calendar_file.write_text(
        json.dumps(events, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def add_calendar_event(
    title: str,
    date: str,
    time: str = "",
    description: str = "",
    location: str = "",
) -> str:
    """
    Dodaj wydarzenie do kalendarza.

    Args:
        title: Tytuł wydarzenia.
        date: Data w formacie YYYY-MM-DD lub opis słowny (np. „jutro", „w piątek").
        time: Godzina w formacie HH:MM (opcjonalnie).
        description: Opis wydarzenia (opcjonalnie).
        location: Miejsce wydarzenia (opcjonalnie).

    Returns:
        Potwierdzenie dodania z ID wydarzenia.
    """
    events = _load_events()

    event = {
        "id": str(uuid.uuid4())[:8],
        "created_at": datetime.now().isoformat(),
        "title": title,
        "date": date,
        "time": time,
        "description": description,
        "location": location,
    }

    events.append(event)
    _persist_events(events)

    time_str = f" o {time}" if time else ""
    loc_str = f" w {location}" if location else ""
    return f"✅ Wydarzenie '{title}' dodane na {date}{time_str}{loc_str} (ID: {event['id']})"


def get_calendar_events(date_from: str = "", date_to: str = "") -> str:
    """
    Pobierz wydarzenia z kalendarza, opcjonalnie filtruj według daty.

    Args:
        date_from: Data początkowa YYYY-MM-DD (opcjonalnie).
        date_to: Data końcowa YYYY-MM-DD (opcjonalnie).

    Returns:
        Lista wydarzeń w formacie JSON.
    """
    events = _load_events()

    if date_from or date_to:
        filtered = []
        for event in events:
            event_date = event.get("date", "")
            if date_from and event_date < date_from:
                continue
            if date_to and event_date > date_to:
                continue
            filtered.append(event)
        events = filtered

    # Sortuj wg daty
    events.sort(key=lambda e: (e.get("date", ""), e.get("time", "")))

    return json.dumps(events, ensure_ascii=False, indent=2)
