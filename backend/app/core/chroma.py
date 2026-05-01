"""
ChromaDB client and knowledge base utilities.
Used by CrewAI agents as a RAG source for event FAQ / seminar details.
"""
from __future__ import annotations

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import settings

_client: chromadb.HttpClient | None = None


def get_chroma_client() -> chromadb.HttpClient:
    global _client
    if _client is None:
        _client = chromadb.HttpClient(
            host=settings.chroma_host,
            port=settings.chroma_port,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _client


def get_collection() -> chromadb.Collection:
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=settings.chroma_collection,
        metadata={"hnsw:space": "cosine"},
    )


def upsert_knowledge(docs: list[str], ids: list[str], metadatas: list[dict] | None = None) -> None:
    """Add or update documents in the knowledge base."""
    collection = get_collection()
    collection.upsert(documents=docs, ids=ids, metadatas=metadatas or [{} for _ in docs])


def query_knowledge(query_text: str, n_results: int = 5) -> list[str]:
    """Query the knowledge base for relevant context."""
    collection = get_collection()
    results = collection.query(query_texts=[query_text], n_results=n_results)
    documents = results.get("documents", [[]])[0]
    return documents


def seed_event_knowledge(campaign_id: int, event_name: str, event_date: str, location: str, faq: list[dict]) -> None:
    """
    Seed event-specific knowledge into ChromaDB.
    Called when a new campaign is created.
    """
    docs = []
    ids = []
    metadatas = []

    base = f"Event: {event_name}. Date: {event_date}. Location: {location}."
    docs.append(base)
    ids.append(f"campaign_{campaign_id}_base")
    metadatas.append({"campaign_id": campaign_id, "type": "event_base"})

    for i, item in enumerate(faq):
        docs.append(f"Q: {item.get('question', '')} A: {item.get('answer', '')}")
        ids.append(f"campaign_{campaign_id}_faq_{i}")
        metadatas.append({"campaign_id": campaign_id, "type": "faq"})

    upsert_knowledge(docs, ids, metadatas)
