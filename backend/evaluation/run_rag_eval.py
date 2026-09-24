from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path

from app.services.rag_service import get_rag_service


def load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSONL at line {line_number}: {exc}"
                ) from exc
    return rows


def normalize(value: str | None) -> str:
    return (value or "").strip().casefold()


def source_matches(
    source: dict,
    expected_document: str | None,
    expected_page: int | None,
) -> bool:
    expected_doc = normalize(expected_document)
    filename = normalize(source.get("source_file"))
    page = source.get("page_number", source.get("page"))

    document_ok = True if not expected_doc else expected_doc in filename
    page_ok = True if expected_page is None else page == expected_page
    return document_ok and page_ok


def keyword_coverage(answer: str, keywords: list[str]) -> float | None:
    clean = [normalize(keyword) for keyword in keywords if normalize(keyword)]
    if not clean:
        return None
    normalized_answer = normalize(answer)
    hits = sum(keyword in normalized_answer for keyword in clean)
    return hits / len(clean)


def evaluate_case(service, project_id: str, case: dict) -> dict:
    question = str(case["question"])
    top_k = int(case.get("top_k", 5))
    threshold = float(case.get("threshold", 0.30))
    should_abstain = bool(case.get("should_abstain", False))
    expected_document = case.get("expected_document")
    expected_page = case.get("expected_page")
    keywords = case.get("answer_keywords") or []

    total_started = time.perf_counter()

    retrieval_started = time.perf_counter()
    retrieved = service.retrieve(
        project_id=project_id,
        query=question,
        top_k=top_k,
        threshold=threshold,
    )
    retrieval_ms = (time.perf_counter() - retrieval_started) * 1000

    sources = service.build_sources(retrieved)

    if retrieved:
        generation_started = time.perf_counter()
        context = service.build_context(retrieved)
        answer_text = service.generate_answer(
            question=question,
            context=context,
        )
        generation_ms = (time.perf_counter() - generation_started) * 1000
        status = "ok"
    else:
        answer_text = "Không đủ thông tin trong tài liệu để trả lời câu hỏi này."
        generation_ms = 0.0
        status = "insufficient_evidence"

    total_ms = (time.perf_counter() - total_started) * 1000

    has_expected_target = bool(expected_document) or expected_page is not None
    retrieval_hit = (
        any(
            source_matches(item, expected_document, expected_page)
            for item in retrieved
        )
        if has_expected_target
        else None
    )
    citation_hit = (
        any(
            source_matches(item, expected_document, expected_page)
            for item in sources
        )
        if has_expected_target
        else None
    )

    abstained = status == "insufficient_evidence"
    abstain_correct = abstained == should_abstain

    return {
        "question": question,
        "status": status,
        "answer": answer_text,
        "sources": sources,
        "retrieved_count": len(retrieved),
        "retrieval_hit": retrieval_hit,
        "citation_hit": citation_hit,
        "abstain_correct": abstain_correct,
        "keyword_coverage": keyword_coverage(answer_text, keywords),
        "retrieval_latency_ms": round(retrieval_ms, 2),
        "generation_latency_ms": round(generation_ms, 2),
        "end_to_end_latency_ms": round(total_ms, 2),
    }


def mean_boolean(values: list[bool | None]) -> float | None:
    filtered = [value for value in values if value is not None]
    if not filtered:
        return None
    return sum(1 for value in filtered if value) / len(filtered)


def mean_number(values: list[float | None]) -> float | None:
    filtered = [value for value in values if value is not None]
    if not filtered:
        return None
    return sum(filtered) / len(filtered)


def evaluate(project_id: str, dataset: list[dict]) -> dict:
    if not dataset:
        raise ValueError("Evaluation dataset is empty")

    service = get_rag_service()
    details = [
        evaluate_case(service, project_id, case)
        for case in dataset
    ]

    retrieval_latencies = [
        row["retrieval_latency_ms"] for row in details
    ]
    generation_latencies = [
        row["generation_latency_ms"] for row in details
        if row["generation_latency_ms"] > 0
    ]
    e2e_latencies = [
        row["end_to_end_latency_ms"] for row in details
    ]

    summary = {
        "count": len(details),
        "retrieval_hit_rate": mean_boolean(
            [row["retrieval_hit"] for row in details]
        ),
        "citation_hit_rate": mean_boolean(
            [row["citation_hit"] for row in details]
        ),
        "abstain_accuracy": mean_boolean(
            [row["abstain_correct"] for row in details]
        ),
        "mean_keyword_coverage": mean_number(
            [row["keyword_coverage"] for row in details]
        ),
        "median_retrieval_latency_ms": round(
            statistics.median(retrieval_latencies), 2
        ),
        "median_generation_latency_ms": (
            round(statistics.median(generation_latencies), 2)
            if generation_latencies
            else 0.0
        ),
        "median_end_to_end_latency_ms": round(
            statistics.median(e2e_latencies), 2
        ),
    }

    return {
        "summary": summary,
        "details": details,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate RAGTutor retrieval, citation and abstention quality."
    )
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result = evaluate(
        project_id=args.project_id,
        dataset=load_jsonl(args.dataset),
    )

    output = json.dumps(result, ensure_ascii=False, indent=2)
    print(output)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")


if __name__ == "__main__":
    main()
