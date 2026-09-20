from app.services.chunking_service import ChunkingService
from app.services.embedding_service import EmbeddingService


class IngestService:
    def __init__(self):
        self.chunking_service = ChunkingService()
        self.embedding_service = EmbeddingService()

    def process_pages(self, pages: list[dict]) -> list[dict]:
        all_chunks = []

        for page in pages:
            page_chunks = self.chunking_service.chunk(
                text=page["text"],
                page_number=page["page"]
            )

            all_chunks.extend(page_chunks)

        for chunk_index, chunk in enumerate(all_chunks):
            chunk["chunk_index"] = chunk_index

        chunk_texts = [
            chunk["content"]
            for chunk in all_chunks
        ]

        embeddings = [
            self.embedding_service.embed(text)
            for text in chunk_texts
        ]

        rows = []

        for chunk, embedding in zip(
            all_chunks,
            embeddings
        ):
            rows.append({
                "content": chunk["content"],
                "page_number": chunk["page_number"],
                "chunk_index": chunk["chunk_index"],
                "embedding": embedding
            })

        return rows

    def save_rows(self, rows: list[dict], supabase, table_name: str):
        if not rows:
            return []

        response = (
            supabase
            .table(table_name)
            .insert(rows)
            .execute()
        )

        return response.data    
    
    def ingest(
    self,
    pages: list[dict],
    supabase,
    table_name: str
    ):
        rows = self.process_pages(pages)

        saved_rows = self.save_rows(
            rows=rows,
            supabase=supabase,
            table_name=table_name
        )

        return saved_rows