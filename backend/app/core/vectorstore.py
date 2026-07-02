from functools import lru_cache

import chromadb

from app.core.config import settings


@lru_cache
def get_chroma_client() -> chromadb.ClientAPI:
    return chromadb.PersistentClient(path=settings.chroma_persist_dir)


def get_listings_collection():
    client = get_chroma_client()
    # Gemini text-embedding-004 (GEMINI_API_KEY gerektirir) prod'da kullanılacak;
    # MVP'de ChromaDB'nin yerel varsayılan embedding fonksiyonu (API anahtarı
    # gerektirmez) ile aynı akış test edilebiliyor. Bkz. TEKNIK_YOL_HARITASI.md.
    return client.get_or_create_collection(name="listings")
