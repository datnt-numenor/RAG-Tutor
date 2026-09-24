from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path

from app.services.rag_service import get_rag_service


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            value = line.strip()
            if not value:
                continue
            try:
                rows.append(json.loads(value))
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSONL at line {line_number}: {exc}"
                ) from exc
    return rows


def contains_expected_source(
    items: list[dict],
    expected_document: str | None,
    expected_page: int | None,
) -> bool:
    if not expected_document and expected_page is None:
        return True

    for item in items:
        filename = item.get("source_file") or ""
        page = item.get("page_number", item.get("page"))
        document_ok = (
            True
            if not expected_document
            else expected_document.casefold() in filename.casefold()
        )
        page_ok = True if expected_page is None else page == expected_page
        if document_ok and page_ok:
            return True
    return False


def keyword_coverage(answer: str, keywords: list[str]) -> float:
    if not keywords:
        return 1.0
    normalized = answer.casefold()
    hits = sum(1 for keyword in keywords if keyword.casefold() in normalized)
    return hits / len(keywords)


def evaluate(project_id: str, dataset: list[dict]) -> dict:
    service = get_rag_service()
    details = []

    for item in dataset:
        question = item["question"]
        should_abstain = bool(item.get("should_abstain", False))
        expected_document = item.get("expected_document")
        expected_page = item.get("expected_page")
        expected_keywords = item.get("answer_keywords") or []

        start = time.perf_counter()
        retrieved = service.retrieve(
            project_id=project_id,
            query=question,
            top_k=int(item.get("top_k", 5)),
            threshold=float(item.get("threshold", 0.30)),
        )
        retrieval_ms = (time.perf_counter() - start) * 1000

        start = time.perf_counter()
        answer = service.answer(
            project_id=project_id,
            question=question,
            top_k=int(item.get("top_k", 5)),
            threshold=float(item.get("threshold", 0.30)),
        )
        total_ms = (time.perf_counter() - start) * 1000

        retrieval_hit = contains_expected_source(
            retrieved,
            expected_document,
            expected_page,
        )
        citation_hit = contains_expected_source(
            answer.get("sources") or [],
            expected_document,
            expected_page,
        )

        abstained = answer["status"] == "insufficient_evidence"
        abstain_correct = abstained == should_abstain
        coverage = keyword_coverage(
            answer.get("answer") or "",
            expected_keywords,
        )

        details.append({
            "question": question,
            "retrieval_hit": retrieval_hit,
            "citation_hit": citation_hit,
            "abstain_correct": abstain_correct,
            "keyword_coverage": round(coverage, 4),
            "retrieved_count": len(retrieved),
            "status": answer["status"],
            "retrieval_ms": round(retrieval_ms, 2),
            "total_ms": round(total_ms, 2),
        })

    count = len(details)
    if count == 0:
        raise ValueError("Evaluation dataset is empty")

    return {
        "count": count,
        "retrieval_hit_rate": round(
            sum(row["retrieval_hit"] for row in details) / count,
            4,
        ),
        "citation_hit_rate": round(
            sum(row["citation_hit"] for row in details) / count,
            4,
        ),
        "abstain_accuracy": round(
            sum(row["abstain_correct"] for row in details) / count,
            4,
        ),
        "mean_keyword_coverage": round(
            statistics.mean(row["keyword_coverage"] for row in details),
            4,
        ),
        "median_retrieval_ms": round(
            statistics.median(row["retrieval_ms"] for row in details),
            2,
        ),
        "median_total_ms": round(
            statistics.median(row["total_ms"] for row in details),
            2,
        ),
        "details": details,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    result = evaluate(
        project_id=args.project_id,
        dataset=load_jsonl(Path(args.dataset)),
    )
    output = json.dumps(result, ensure_ascii=False, indent=2)
    print(output)

    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")


if __name__ == "__main__":
    main()
