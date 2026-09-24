from app.services.chunking_service import ChunkingService


def word_token_counter(text: str) -> int:
    return len(text.split()) + 2


def test_vietnamese_abbreviation_does_not_split_wrongly():
    service = ChunkingService(
        token_counter=word_token_counter,
        model_max_tokens=64,
    )
    sentences = service.split_sentences(
        "TS. Nguyễn Văn A làm việc tại TP.HCM. Đây là câu tiếp theo."
    )

    assert len(sentences) == 2
    assert sentences[0].startswith("TS. Nguyễn Văn A")
    assert "TP.HCM" in sentences[0]


def test_chunks_respect_model_token_limit():
    service = ChunkingService(
        token_counter=word_token_counter,
        model_max_tokens=28,
        overlap_sentences=1,
    )
    text = " ".join(
        f"Đây là câu số {i} có một số từ để kiểm tra chunking."
        for i in range(1, 20)
    )

    chunks = service.chunk(text=text, page_number=3)

    assert chunks
    assert all(chunk["token_count"] <= service.max_tokens for chunk in chunks)
    assert all(chunk["page_number"] == 3 for chunk in chunks)


def test_heading_and_source_metadata_are_kept():
    service = ChunkingService(
        token_counter=word_token_counter,
        model_max_tokens=80,
    )
    chunks = service.chunk(
        text=(
            "CHƯƠNG 1 MẠNG NƠ-RON\n"
            "Mạng nơ-ron gồm nhiều lớp. Mỗi lớp biến đổi đầu vào.\n\n"
            "1.1 LAN TRUYỀN TIẾN\n"
            "Dữ liệu đi từ lớp đầu vào đến lớp đầu ra."
        ),
        page_number=7,
    )

    assert chunks
    assert any(chunk.get("section_title") for chunk in chunks)
    for chunk in chunks:
        assert chunk["source_spans"][0]["page_number"] == 7
        assert "sentence_start" in chunk["source_spans"][0]
        assert "sentence_end" in chunk["source_spans"][0]
