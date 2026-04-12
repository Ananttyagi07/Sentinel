import hashlib
import re
import uuid
from dataclasses import dataclass

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions


def _normalize_text(text: str) -> str:
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _chunk_text(text: str, chunk_size: int = 1400, overlap: int = 220) -> list[str]:
    text = _normalize_text(text)
    if not text:
        return []

    chunks: list[str] = []
    step = max(200, chunk_size - overlap)
    for i in range(0, len(text), step):
        chunk = text[i:i + chunk_size].strip()
        if chunk:
            chunks.append(chunk)
        if i + chunk_size >= len(text):
            break
    return chunks


@dataclass
class SessionPageState:
    url: str
    content_hash: str
    collection_name: str


class SessionPageRAG:
    def __init__(self):
        self.client = chromadb.Client(
            Settings(anonymized_telemetry=False, allow_reset=False)
        )
        self.embedding_fn = embedding_functions.OpenAIEmbeddingFunction(
            api_key_env_var="OPENAI_API_KEY",
            model_name="text-embedding-3-small",
        )
        self._session_state: dict[str, SessionPageState] = {}

    @staticmethod
    def _content_hash(content: str) -> str:
        return hashlib.sha256((content or "").encode("utf-8")).hexdigest()

    @staticmethod
    def _collection_name(session_id: str) -> str:
        safe = re.sub(r"[^a-zA-Z0-9_-]", "_", session_id)[:40] or "session"
        return f"sentinel_{safe}_{uuid.uuid4().hex[:8]}"

    def _delete_collection_safely(self, collection_name: str):
        try:
            self.client.delete_collection(name=collection_name)
        except Exception:
            pass

    def ensure_page_index(self, session_id: str, url: str, page_content: str) -> dict:
        content = _normalize_text(page_content)
        content_hash = self._content_hash(content)
        print("Current page URL: ", url)
        existing = self._session_state.get(session_id)
        if existing and existing.url == url:
            return {"status": "reused", "url": url, "chunks": None}

        if existing:
            self._delete_collection_safely(existing.collection_name)

        collection_name = self._collection_name(session_id)
        collection = self.client.create_collection(
            name=collection_name,
            embedding_function=self.embedding_fn,
            metadata={"hnsw:space": "cosine"},
        )

        chunks = _chunk_text(content)
        if chunks:
            ids = [f"chunk_{i}" for i in range(len(chunks))]
            metadatas = [{"url": url, "chunk_index": i} for i in range(len(chunks))]
            collection.add(ids=ids, documents=chunks, metadatas=metadatas)

        self._session_state[session_id] = SessionPageState(
            url=url,
            content_hash=content_hash,
            collection_name=collection_name,
        )
        return {"status": "rebuilt", "url": url, "chunks": len(chunks)}

    def query_page(self, session_id: str, query: str, top_k: int = 6) -> list[str]:
        existing = self._session_state.get(session_id)
        if not existing:
            return []

        try:
            collection = self.client.get_collection(
                name=existing.collection_name,
                embedding_function=self.embedding_fn,
            )
            result = collection.query(query_texts=[query], n_results=top_k)
            documents = result.get("documents") or []
            return documents[0] if documents else []
        except Exception:
            return []