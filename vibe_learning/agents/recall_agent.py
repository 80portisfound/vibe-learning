import os
from typing import List, Dict, Optional


class RecallAgent:
    """Vectorizes notes and stores them in ChromaDB.
    This agent itself is a hands-on RAG experience.
    """

    def __init__(self, db_path: str = ".vibe-learning/chroma_db"):
        self.db_path = db_path
        self._client = None
        self._collection = None
        self._embedder = None
        self._init_db()

    def _init_db(self):
        try:
            import chromadb
            from sentence_transformers import SentenceTransformer
            self._client = chromadb.PersistentClient(path=self.db_path)
            self._collection = self._client.get_or_create_collection("vibe_notes")
            self._embedder = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception as e:
            print(f"[RecallAgent] ChromaDB init failed: {e}")
            self._client = None
            self._collection = None
            self._embedder = None

    def index_note(self, note_path: str, note_content: str, metadata: dict) -> bool:
        if self._collection is None or self._embedder is None:
            return False
        try:
            embedding = self._embedder.encode(note_content).tolist()
            doc_id = os.path.basename(note_path)
            self._collection.add(
                ids=[doc_id],
                embeddings=[embedding],
                documents=[note_content],
                metadatas=[metadata],
            )
            return True
        except Exception as e:
            print(f"[RecallAgent] index_note failed: {e}")
            return False

    def recall(self, query: str, n_results: int = 3) -> List[Dict]:
        if self._collection is None or self._embedder is None:
            return []
        try:
            embedding = self._embedder.encode(query).tolist()
            results = self._collection.query(
                query_embeddings=[embedding],
                n_results=n_results,
            )
            formatted = []
            ids = results.get("ids", [[]])[0]
            docs = results.get("documents", [[]])[0]
            metas = results.get("metadatas", [[]])[0]
            distances = results.get("distances", [[]])[0]
            for i, doc_id in enumerate(ids):
                formatted.append({
                    "id": doc_id,
                    "content": docs[i] if i < len(docs) else "",
                    "metadata": metas[i] if i < len(metas) else {},
                    "distance": distances[i] if i < len(distances) else 0.0,
                })
            return formatted
        except Exception as e:
            print(f"[RecallAgent] recall failed: {e}")
            return []

    def list_concepts(self) -> List[str]:
        if self._collection is None:
            return []
        try:
            data = self._collection.get()
            concepts = set()
            for meta in data.get("metadatas", []):
                if meta and "concept" in meta:
                    concepts.add(meta["concept"])
            return sorted(list(concepts))
        except Exception as e:
            print(f"[RecallAgent] list_concepts failed: {e}")
            return []
