"""Rozwiązywanie nazwy modelu Ollama – sprawdza, czy skonfigurowany model jest
zainstalowany, a jeśli nie, używa dostępnego zamiennika zamiast wywalać błąd.
"""

import logging

import httpx

from backend.config import settings

logger = logging.getLogger(__name__)

_resolved_model: str | None = None


async def get_ollama_model() -> str:
    """Zwraca nazwę modelu do użycia z Ollamą – wynik cache'owany na cały proces."""
    global _resolved_model
    if _resolved_model is not None:
        return _resolved_model

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.ollama_base_url}/api/tags")
            resp.raise_for_status()
            models = resp.json().get("models", [])
    except Exception:
        logger.warning(
            "Nie udało się pobrać listy modeli z Ollamy (%s) – używam skonfigurowanego '%s'",
            settings.ollama_base_url,
            settings.ollama_model,
        )
        return settings.ollama_model

    names = [m["name"] for m in models]

    if settings.ollama_model in names:
        _resolved_model = settings.ollama_model
        return _resolved_model

    fallback = next(
        (m["name"] for m in models if "completion" in m.get("capabilities", [])),
        names[0] if names else settings.ollama_model,
    )
    logger.warning(
        "Model '%s' niedostępny w Ollamie. Dostępne: %s. Używam zamiast tego: '%s'",
        settings.ollama_model,
        names,
        fallback,
    )
    _resolved_model = fallback
    return _resolved_model
