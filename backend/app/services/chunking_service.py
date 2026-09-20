import re


class ChunkingService:
    def split_sentences(self, text: str) -> list[str]:
        return re.split(r'(?<=[.!?])\s+', text)

    def chunk(
        self,
        text: str,
        page_number: int,
        sentences_per_chunk: int = 2,
        overlap: int = 1
    ) -> list[dict]:
        sentences = self.split_sentences(text)

        chunks = []

        step = sentences_per_chunk - overlap

        for i in range(0, len(sentences), step):
            chunk_sentences = sentences[i:i + sentences_per_chunk]

            if not chunk_sentences:
                continue

            chunk_text = " ".join(chunk_sentences).strip()

            if not chunk_text:
                continue

            chunks.append({
                "content": chunk_text,
                "page_number": page_number
            })

        return chunks