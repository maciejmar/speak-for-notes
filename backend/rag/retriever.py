"""
RAG Retriever – pobieranie kontekstu z Qdrant do generowania odpowiedzi.

Pipeline:
  zapytanie użytkownika → embedding → Qdrant search → formatowanie kontekstu
"""

from langchain_core.documents import Document
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

from backend.config import settings
from backend.rag.embeddings import get_embeddings


def _get_vector_store() -> QdrantVectorStore:
    """Utwórz połączenie z kolekcją Qdrant przez LangChain."""
    client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
    return QdrantVectorStore(
        client=client,
        collection_name=settings.qdrant_collection,
        embedding=get_embeddings(),
        content_payload_key="content",
        metadata_payload_key="metadata",
    )


async def retrieve_relevant_notes(
    query: str,
    k: int = 4,
    category_filter: str = "",
) -> list[Document]:
    """
    Pobierz k najistotniejszych notatek dla zapytania (RAG retrieval).

    Args:
        query: Pytanie lub temat do wyszukania.
        k: Liczba dokumentów do pobrania.
        category_filter: Opcjonalne filtrowanie według kategorii.

    Returns:
        Lista dokumentów LangChain z treścią i metadanymi.
    """
    try:
        store = _get_vector_store()

        if category_filter:
            docs = await store.asimilarity_search(
                query,
                k=k,
                filter={"category": category_filter},
            )
        else:
            docs = await store.asimilarity_search(query, k=k)

        return docs

    except Exception:
        return []


def format_context(documents: list[Document]) -> str:
    """
    Formatuj pobrane dokumenty jako kontekst dla LLM.

    Args:
        documents: Lista dokumentów z Qdrant.

    Returns:
        Sformatowany blok kontekstowy.
    """
    if not documents:
        return "Brak powiązanych notatek w bazie wiedzy."

    parts = []
    for i, doc in enumerate(documents, 1):
        meta = doc.metadata
        category = meta.get("category", "general")
        created = meta.get("created_at", "")[:10]
        enrichment = meta.get("enrichment", "")

        note_text = f"{i}. [{category.upper()}] ({created})\n   {doc.page_content}"
        if enrichment:
            note_text += f"\n   Kontekst: {enrichment[:200]}..."
        parts.append(note_text)

    return "\n\n".join(parts)


async def get_rag_context(query: str, k: int = 4) -> str:
    """
    Pełny pipeline RAG: pobierz dokumenty i zwróć sformatowany kontekst.

    Args:
        query: Zapytanie użytkownika.
        k: Liczba dokumentów.

    Returns:
        Kontekst gotowy do przekazania do LLM.
    """
    docs = await retrieve_relevant_notes(query, k=k)
    return format_context(docs)
