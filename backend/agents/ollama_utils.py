"""Rozwiązywanie nazwy modelu Ollama – sprawdza, czy skonfigurowany model jest
zainstalowany, a jeśli nie, używa dostępnego zamiennika zamiast wywalać błąd.

Zawiera też fallback na płatny model API (gdy Ollama zawiedzie) razem
ze śledzeniem kosztów tych wywołań.
"""

import json
import logging
from datetime import datetime
from typing import Any, TypeVar

from langchain_core.messages import BaseMessage
from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI
from pydantic import BaseModel
import httpx

from backend.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

# Cennik OpenAI, USD za 1M tokenów (stan: lipiec 2026)
# https://developers.openai.com/api/docs/pricing
_PRICING: dict[str, dict[str, float]] = {
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
}

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


def get_fallback_llm(temperature: float = 0) -> ChatOpenAI:
    """Tani model API (OpenAI) używany, gdy lokalna Ollama zawiedzie."""
    return ChatOpenAI(
        model=settings.fallback_model,
        api_key=settings.openai_api_key,
        temperature=temperature,
    )


async def invoke_with_fallback(
    primary: Runnable,
    messages: list[BaseMessage],
    *,
    schema: type[T] | None = None,
    temperature: float = 0,
    agent_name: str = "",
) -> Any:
    """
    Wywołaj primary (Ollama). Jeśli zawiedzie, przełącz na tani model API
    i zapisz koszt tego wywołania (koszt lokalnej Ollamy = 0, więc nie
    ma czego liczyć przy sukcesie).
    """
    try:
        return await primary.ainvoke(messages)
    except Exception as e:
        logger.warning("Ollama zawiodła w '%s' (%s) – fallback na %s", agent_name, e, settings.fallback_model)

        fallback_chat = get_fallback_llm(temperature=temperature)

        if schema is not None:
            fallback = fallback_chat.with_structured_output(schema, include_raw=True)
            raw_result = await fallback.ainvoke(messages)
            _record_cost(agent_name, raw_result["raw"].usage_metadata)
            return raw_result["parsed"]

        response = await fallback_chat.ainvoke(messages)
        _record_cost(agent_name, response.usage_metadata)
        return response


def _record_cost(agent_name: str, usage: dict | None) -> None:
    if not usage:
        return

    model = settings.fallback_model
    price = _PRICING.get(model, {"input": 0.15, "output": 0.60})
    input_tokens = usage.get("input_tokens", 0)
    output_tokens = usage.get("output_tokens", 0)
    cost = (input_tokens / 1_000_000) * price["input"] + (output_tokens / 1_000_000) * price["output"]

    settings.data_dir.mkdir(parents=True, exist_ok=True)
    entries = []
    if settings.costs_file.exists():
        entries = json.loads(settings.costs_file.read_text(encoding="utf-8"))

    entries.append({
        "timestamp": datetime.now().isoformat(),
        "agent": agent_name,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": round(cost, 6),
    })
    settings.costs_file.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")

    logger.info("Koszt fallbacku (%s, %s): $%.6f", agent_name, model, cost)


def get_cost_summary() -> dict:
    """Zagregowane statystyki kosztów wywołań fallbackowego LLM."""
    if not settings.costs_file.exists():
        return {
            "total_cost_usd": 0.0,
            "total_calls": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "by_agent": {},
            "recent": [],
            "model": settings.fallback_model,
        }

    entries: list[dict] = json.loads(settings.costs_file.read_text(encoding="utf-8"))

    by_agent: dict[str, dict] = {}
    for e in entries:
        stats = by_agent.setdefault(e["agent"], {"calls": 0, "cost_usd": 0.0})
        stats["calls"] += 1
        stats["cost_usd"] += e["cost_usd"]
    for stats in by_agent.values():
        stats["cost_usd"] = round(stats["cost_usd"], 6)

    return {
        "total_cost_usd": round(sum(e["cost_usd"] for e in entries), 6),
        "total_calls": len(entries),
        "total_input_tokens": sum(e["input_tokens"] for e in entries),
        "total_output_tokens": sum(e["output_tokens"] for e in entries),
        "by_agent": by_agent,
        "recent": list(reversed(entries[-20:])),
        "model": settings.fallback_model,
    }
