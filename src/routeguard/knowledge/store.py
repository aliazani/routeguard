from dataclasses import dataclass

import chromadb
from chromadb.api.types import Metadata
from sentence_transformers import SentenceTransformer


@dataclass(frozen=True)
class SearchResult:
    text: str
    source: str
    document_id: str
    chunk_index: int
    score: float


class KnowledgeStore:
    def __init__(
        self,
        persist_directory: str = ".chroma",
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
    ) -> None:
        self.client = chromadb.PersistentClient(path=persist_directory)

        self.collection = self.client.get_or_create_collection(
            name="routeguard-policies",
            metadata={
                "hnsw:space": "cosine",
            },
        )

        self.embedding_model = SentenceTransformer(model_name)

    def add_document(
        self,
        *,
        document_id: str,
        text: str,
        source: str,
    ) -> None:
        chunks = self._chunk_text(text)

        if not chunks:
            return

        embeddings = self.embedding_model.encode(
            chunks,
            normalize_embeddings=True,
        ).tolist()

        ids = [f"{document_id}:{index}" for index in range(len(chunks))]

        metadatas: list[Metadata] = [
            {
                "source": source,
                "document_id": document_id,
                "chunk_index": str(index),
            }
            for index in range(len(chunks))
        ]

        self.collection.upsert(
            ids=ids,
            documents=chunks,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    def search(
        self,
        query: str,
        *,
        limit: int = 3,
        min_score: float | None = None,
    ) -> list[SearchResult]:
        query = query.strip()

        if not query:
            return []

        if limit < 1:
            return []

        if self.collection.count() == 0:
            return []

        query_embedding = self.embedding_model.encode(
            [query],
            normalize_embeddings=True,
        ).tolist()

        result = self.collection.query(
            query_embeddings=query_embedding,
            n_results=limit,
        )

        documents = result.get("documents")
        metadatas = result.get("metadatas")
        distances = result.get("distances")

        if not documents or not metadatas or not distances or not documents[0]:
            return []

        results: list[SearchResult] = []

        for document, metadata, distance in zip(
            documents[0],
            metadatas[0],
            distances[0],
            strict=True,
        ):
            if document is None or metadata is None:
                continue

            source_value = metadata.get("source")

            document_id_value = metadata.get("document_id")

            chunk_index_value = metadata.get("chunk_index")

            if not isinstance(
                source_value,
                str,
            ):
                continue

            if not isinstance(
                document_id_value,
                str,
            ):
                continue

            if not isinstance(
                chunk_index_value,
                str,
            ):
                continue

            try:
                chunk_index = int(chunk_index_value)
            except ValueError:
                continue

            score = 1.0 - float(distance)

            if min_score is not None and score < min_score:
                continue

            results.append(
                SearchResult(
                    text=document,
                    source=source_value,
                    document_id=(document_id_value),
                    chunk_index=(chunk_index),
                    score=score,
                )
            )

        return results

    @staticmethod
    def _chunk_text(
        text: str,
        *,
        chunk_size: int = 700,
        overlap: int = 100,
    ) -> list[str]:
        text = text.strip()

        if not text:
            return []

        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than zero")

        if overlap < 0:
            raise ValueError("overlap cannot be negative")

        if overlap >= chunk_size:
            raise ValueError("overlap must be smaller than chunk_size")

        chunks: list[str] = []
        start = 0

        while start < len(text):
            end = min(
                start + chunk_size,
                len(text),
            )

            chunk = text[start:end].strip()

            if chunk:
                chunks.append(chunk)

            if end >= len(text):
                break

            start = end - overlap

        return chunks
