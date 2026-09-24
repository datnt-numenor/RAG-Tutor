from evaluation.run_rag_eval import keyword_coverage, source_matches


def test_source_matches_filename_and_page():
    source = {
        "source_file": "attention_transformer.pdf",
        "page": 7,
    }
    assert source_matches(source, "transformer.pdf", 7)
    assert not source_matches(source, "transformer.pdf", 8)
    assert not source_matches(source, "biology.pdf", 7)


def test_source_matches_retrieval_page_number_shape():
    source = {
        "source_file": "lecture.pdf",
        "page_number": 3,
    }
    assert source_matches(source, "lecture.pdf", 3)


def test_keyword_coverage_is_case_insensitive():
    result = keyword_coverage(
        "Attention dùng Query, Key và Value.",
        ["query", "KEY", "value", "softmax"],
    )
    assert result == 0.75


def test_keyword_coverage_returns_none_without_keywords():
    assert keyword_coverage("anything", []) is None
