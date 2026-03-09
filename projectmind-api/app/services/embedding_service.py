"""
Geração de embeddings para pgvector (1536 dimensões - OpenAI compatible).
"""
from app.config import settings


class EmbeddingService:
    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None and settings.openai_api_key:
            from openai import OpenAI
            self._client = OpenAI(api_key=settings.openai_api_key)
        return self._client

    def generate_embedding_sync(self, text: str) -> list[float]:
        """Gera embedding síncrono (1536 dims)."""
        client = self._get_client()
        if not client:
            return []
        try:
            r = client.embeddings.create(
                model="text-embedding-3-small",
                input=text[:8000],
            )
            return r.data[0].embedding
        except Exception:
            return []

    async def generate_embedding_async(self, text: str) -> list[float]:
        """Gera embedding de forma assíncrona."""
        import asyncio
        return await asyncio.to_thread(self.generate_embedding_sync, text)
