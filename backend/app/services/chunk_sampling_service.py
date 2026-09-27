from __future__ import annotations

import math
from typing import Any


def sample_evenly(rows: list[dict], count: int) -> list[dict]:
    """Select up to count rows distributed across the full ordered input."""
    if count <= 0 or not rows:
        return []
    if len(rows) <= count:
        return list(rows)
    if count == 1:
        return [rows[len(rows) // 2]]

    indexes = [
        round(index * (len(rows) - 1) / (count - 1))
        for index in range(count)
    ]
    # round() can theoretically repeat an index for unusual ratios.
    seen: set[int] = set()
    output: list[dict] = []
    for index in indexes:
        if index not in seen:
            output.append(rows[index])
            seen.add(index)

    if len(output) < count:
        for index, row in enumerate(rows):
            if index in seen:
                continue
            output.append(row)
            if len(output) >= count:
                break
    return output


def interleave_groups(
    groups: list[list[dict]],
    limit: int,
) -> list[dict]:
    """Round-robin rows from groups so one document cannot dominate."""
    if limit <= 0:
        return []

    output: list[dict] = []
    cursor = 0
    while len(output) < limit:
        added = False
        for group in groups:
            if cursor < len(group):
                output.append(group[cursor])
                added = True
                if len(output) >= limit:
                    break
        if not added:
            break
        cursor += 1
    return output


def balanced_active_chunks(
    supabase: Any,
    project_id: str,
    limit: int,
    *,
    max_documents: int = 50,
    max_chunks_per_document: int = 240,
) -> list[dict]:
    """
    Return chunks from active, ready document versions while balancing sources.

    This intentionally does not use a global LIMIT on chunks because insertion
    order can otherwise make a long document consume the whole LLM context.
    """
    if limit <= 0:
        return []

    documents = (
        supabase.table("documents")
        .select(
            "id, active_version_id, status, "
            "document_versions!active_version_id("
            "id, original_filename, status)"
        )
        .eq("project_id", project_id)
        .eq("status", "active")
        .not_.is_("active_version_id", "null")
        .limit(max_documents)
        .execute()
    ).data or []

    ready_documents: list[dict] = []
    for document in documents:
        version = document.get("document_versions") or {}
        active_version_id = document.get("active_version_id")
        if (
            active_version_id
            and version.get("id") == active_version_id
            and version.get("status") == "ready"
        ):
            ready_documents.append(document)

    if not ready_documents:
        return []

    per_document_target = max(
        1,
        math.ceil(limit / len(ready_documents)),
    )

    active_version_ids = [
        document["active_version_id"]
        for document in ready_documents
    ]
    fetched_rows = (
        supabase.table("chunks")
        .select(
            "id, content, page_number, section_title, chunk_index, "
            "document_id, document_version_id"
        )
        .eq("project_id", project_id)
        .in_("document_version_id", active_version_ids)
        .order("document_id")
        .order("chunk_index")
        .limit(max_documents * max_chunks_per_document)
        .execute()
    ).data or []

    rows_by_version: dict[str, list[dict]] = {
        version_id: [] for version_id in active_version_ids
    }
    for row in fetched_rows:
        version_id = row.get("document_version_id")
        group = rows_by_version.get(version_id)
        if group is not None and len(group) < max_chunks_per_document:
            group.append(row)

    prepared: list[tuple[dict, list[dict]]] = []
    for document in ready_documents:
        active_version_id = document["active_version_id"]
        version = document.get("document_versions") or {}
        rows = rows_by_version.get(active_version_id, [])

        for row in rows:
            row["document_versions"] = {
                "id": active_version_id,
                "original_filename": version.get("original_filename"),
                "status": version.get("status"),
            }
            row["documents"] = {
                "active_version_id": active_version_id,
                "status": "active",
            }
        prepared.append((document, rows))

    sampled_groups = [
        sample_evenly(rows, per_document_target)
        for _, rows in prepared
    ]
    first_pass = interleave_groups(sampled_groups, limit)
    if len(first_pass) >= limit:
        return first_pass

    # Some documents may contain fewer chunks than their initial quota.
    # Re-sample the already fetched rows at a wider target and interleave again.
    refill_target = min(
        max_chunks_per_document,
        max(per_document_target, limit),
    )
    refill_groups = [
        sample_evenly(rows, refill_target)
        for _, rows in prepared
    ]
    return interleave_groups(refill_groups, limit)
