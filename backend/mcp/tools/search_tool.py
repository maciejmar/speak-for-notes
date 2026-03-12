"""Narzędzie MCP do wyszukiwania w internecie (DuckDuckGo)."""

from duckduckgo_search import DDGS


def web_search(query: str, max_results: int = 3, language: str = "pl-PL") -> str:
    """
    Wyszukaj informacje w internecie za pomocą DuckDuckGo.

    Args:
        query: Zapytanie wyszukiwania.
        max_results: Maksymalna liczba wyników (domyślnie 3).
        language: Język wyników (domyślnie pl-PL).

    Returns:
        Sformatowane wyniki wyszukiwania.
    """
    try:
        with DDGS() as ddgs:
            results = list(
                ddgs.text(query, max_results=max_results, region=language)
            )

        if not results:
            return "Brak wyników wyszukiwania."

        formatted = []
        for i, r in enumerate(results, 1):
            title = r.get("title", "Brak tytułu")
            body = r.get("body", "Brak opisu")
            href = r.get("href", "")
            formatted.append(f"{i}. **{title}**\n{body}\nŹródło: {href}")

        return "\n\n".join(formatted)

    except Exception as e:
        return f"Błąd wyszukiwania: {e}"
