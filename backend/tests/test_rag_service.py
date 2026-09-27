from app.services.rag_service import RAGService


def make_service() -> RAGService:
    service = object.__new__(RAGService)
    service.gemini_model = "test-model"
    return service


def test_build_sources_deduplicates_same_version_and_page():
    service = make_service()
    results = [
        {
            "id": "chunk-1",
            "document_id": "doc-1",
            "document_version_id": "version-1",
            "source_file": "lecture.pdf",
            "page_number": 4,
            "similarity": 0.8,
        },
        {
            "id": "chunk-2",
            "document_id": "doc-1",
            "document_version_id": "version-1",
            "source_file": "lecture.pdf",
            "page_number": 4,
            "similarity": 0.75,
        },
    ]

    sources = service.build_sources(results)

    assert len(sources) == 1
    assert sources[0]["source_file"] == "lecture.pdf"
    assert sources[0]["page"] == 4


def test_answer_abstains_without_retrieval_evidence():
    service = make_service()
    service.retrieve = lambda **kwargs: []

    result = service.answer(
        project_id="project-1",
        question="Câu hỏi không có trong tài liệu",
    )

    assert result["status"] == "insufficient_evidence"
    assert result["sources"] == []
    assert result["retrieval_params"]["retrieved_count"] == 0


def test_answer_returns_sources_when_evidence_exists():
    service = make_service()
    evidence = [
        {
            "id": "chunk-1",
            "content": "Attention dùng query, key và value.",
            "page_number": 2,
            "chunk_index": 0,
            "document_id": "doc-1",
            "document_version_id": "version-1",
            "source_file": "transformer.pdf",
            "similarity": 0.91,
        }
    ]
    service.retrieve = lambda **kwargs: evidence
    service.generate_answer = lambda question, context: "Attention dùng Q, K, V."

    result = service.answer(
        project_id="project-1",
        question="Attention dùng gì?",
    )

    assert result["status"] == "ok"
    assert result["answer"] == "Attention dùng Q, K, V."
    assert result["sources"][0]["source_file"] == "transformer.pdf"
    assert result["sources"][0]["page"] == 2
