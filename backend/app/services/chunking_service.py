from __future__ import annotations

import re
from collections.abc import Callable


class ChunkingService:
    VERSION = "vi-token-semantic-v2"

    _ABBREVIATIONS = (
        "TP.HCM",
        "TP.",
        "GS.",
        "PGS.",
        "TS.",
        "ThS.",
        "BS.",
        "Mr.",
        "Mrs.",
        "Dr.",
        "Prof.",
        "v.v.",
        "v.d.",
    )

    def __init__(
        self,
        token_counter: Callable[[str], int],
        model_max_tokens: int,
        overlap_sentences: int = 1,
    ):
        self.token_counter = token_counter
        self.max_tokens = max(48, int(model_max_tokens) - 8)
        self.target_tokens = max(32, min(220, int(self.max_tokens * 0.82)))
        self.overlap_sentences = max(0, overlap_sentences)

    def _is_heading(self, line: str) -> bool:
        value = line.strip()
        if not value or len(value) > 140:
            return False

        if re.match(
            r"^(chương|chapter|phần|part|mục|section)\s+[\divxlc]+",
            value,
            flags=re.I,
        ):
            return True
        if re.match(r"^\d+(?:\.\d+){0,4}\s+\S+", value):
            return True

        letters = [char for char in value if char.isalpha()]
        if len(letters) >= 4:
            uppercase_ratio = sum(char.isupper() for char in letters) / len(letters)
            if uppercase_ratio >= 0.72 and len(value.split()) <= 14:
                return True

        return False

    def _protect_boundaries(self, text: str) -> str:
        protected = text
        for index, abbreviation in enumerate(self._ABBREVIATIONS):
            protected = protected.replace(
                abbreviation,
                abbreviation.replace(".", f"§{index}§"),
            )

        protected = re.sub(
            r"(?<=\d)\.(?=\d)",
            "§DECIMAL§",
            protected,
        )
        return protected

    def _restore_boundaries(self, text: str) -> str:
        restored = text.replace("§DECIMAL§", ".")
        for index, abbreviation in enumerate(self._ABBREVIATIONS):
            restored = restored.replace(
                abbreviation.replace(".", f"§{index}§"),
                abbreviation,
            )
        return restored

    def split_sentences(self, text: str) -> list[str]:
        clean = re.sub(r"[ \t]+", " ", text.strip())
        if not clean:
            return []

        protected = self._protect_boundaries(clean)
        parts = re.split(r"(?<=[.!?…])\s+(?=[^\s])", protected)
        sentences = [
            self._restore_boundaries(part).strip()
            for part in parts
            if self._restore_boundaries(part).strip()
        ]
        return sentences or [clean]

    def _split_long_text(self, text: str) -> list[str]:
        if self.token_counter(text) <= self.max_tokens:
            return [text]

        clauses = [
            part.strip()
            for part in re.split(r"(?<=[;,:])\s+", text)
            if part.strip()
        ]

        if len(clauses) > 1:
            result: list[str] = []
            current: list[str] = []
            for clause in clauses:
                candidate = " ".join(current + [clause]).strip()
                if current and self.token_counter(candidate) > self.max_tokens:
                    result.extend(self._split_long_text(" ".join(current)))
                    current = [clause]
                else:
                    current.append(clause)
            if current:
                result.extend(self._split_long_text(" ".join(current)))
            return result

        words = text.split()
        result = []
        current_words: list[str] = []

        for word in words:
            candidate = " ".join(current_words + [word])
            if current_words and self.token_counter(candidate) > self.max_tokens:
                result.append(" ".join(current_words))
                current_words = [word]
            else:
                current_words.append(word)

        if current_words:
            result.append(" ".join(current_words))

        return [part for part in result if part.strip()]

    def _units(self, text: str) -> list[dict]:
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        raw_lines = [line.strip() for line in normalized.split("\n")]

        units: list[dict] = []
        section_title: str | None = None
        sentence_index = 0
        paragraph_lines: list[str] = []

        def flush_paragraph() -> None:
            nonlocal sentence_index
            if not paragraph_lines:
                return

            paragraph = " ".join(paragraph_lines).strip()
            paragraph_lines.clear()
            if not paragraph:
                return

            for sentence in self.split_sentences(paragraph):
                for piece in self._split_long_text(sentence):
                    units.append({
                        "text": piece,
                        "section_title": section_title,
                        "sentence_index": sentence_index,
                    })
                    sentence_index += 1

        for line in raw_lines:
            if not line:
                flush_paragraph()
                continue

            if self._is_heading(line):
                flush_paragraph()
                section_title = line
                continue

            paragraph_lines.append(line)

        flush_paragraph()
        return units

    def chunk(self, text: str, page_number: int) -> list[dict]:
        units = self._units(text)
        if not units:
            return []

        chunks: list[dict] = []
        current: list[dict] = []

        def render(items: list[dict]) -> str:
            body = " ".join(item["text"] for item in items).strip()
            section = next(
                (
                    item["section_title"]
                    for item in reversed(items)
                    if item.get("section_title")
                ),
                None,
            )
            if section and not body.startswith(section):
                return f"{section}\n{body}"
            return body

        def flush() -> None:
            nonlocal current
            if not current:
                return

            content = render(current)
            if not content:
                current = []
                return

            section_title = next(
                (
                    item["section_title"]
                    for item in reversed(current)
                    if item.get("section_title")
                ),
                None,
            )
            sentence_indexes = [item["sentence_index"] for item in current]

            chunks.append({
                "content": content,
                "page_number": page_number,
                "section_title": section_title,
                "token_count": self.token_counter(content),
                "source_spans": [{
                    "page_number": page_number,
                    "sentence_start": min(sentence_indexes),
                    "sentence_end": max(sentence_indexes),
                    "section_title": section_title,
                }],
            })

            if self.overlap_sentences > 0:
                current = current[-self.overlap_sentences :]
            else:
                current = []

        for unit in units:
            candidate = render(current + [unit])

            if current and (
                self.token_counter(candidate) > self.target_tokens
                or self.token_counter(candidate) > self.max_tokens
            ):
                flush()

            candidate_after_flush = render(current + [unit])
            if self.token_counter(candidate_after_flush) > self.max_tokens:
                if current:
                    flush()
                current = [unit]
                if self.token_counter(render(current)) >= self.max_tokens:
                    flush()
            else:
                current.append(unit)

        flush()

        return [
            chunk
            for chunk in chunks
            if chunk["content"].strip() and chunk["token_count"] <= self.max_tokens
        ]
