"""Moduł embeddingów – generowanie wektorów dla RAG."""

from functools import lru_cache

from langchain_openai import OpenAIEmbeddings

from backend.config import settings


@lru_cache(maxsize=1)
def get_embeddings() -> OpenAIEmbeddings:
    """Singleton embeddera OpenAI (text-embedding-3-small)."""
    return OpenAIEmbeddings(
        model=settings.embedding_model,
        openai_api_key=settings.openai_api_key,
    )


async def embed_text(text: str) -> list[float]:
    """Wygeneruj embedding dla tekstu."""
    embedder = get_embeddings()
    return await embedder.aembed_query(text)


async def embed_documents(texts: list[str]) -> list[list[float]]:
    """Wygeneruj embeddingi dla wielu dokumentów."""
    embedder = get_embeddings()
    return await embedder.aembed_documents(texts)
