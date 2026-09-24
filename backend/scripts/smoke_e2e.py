from __future__ import annotations

import argparse
import json
import os
import tempfile
import time
from pathlib import Path

import httpx
from docx import Document


TEST_TEXT = """
Cơ chế attention trong Transformer sử dụng ba vector chính: Query, Key và Value.
Scaled dot-product attention tính độ tương đồng giữa Query và Key, chia cho căn
bậc hai của chiều key, sau đó dùng softmax để tạo trọng số. Các trọng số này
được dùng để kết hợp các Value. Self-attention cho phép mỗi token tham chiếu
các token khác trong cùng chuỗi.
""".strip()


def make_docx(path: Path) -> None:
    document = Document()
    document.add_heading("Transformer Attention", level=1)
    document.add_paragraph(TEST_TEXT)
    document.add_heading("Ứng dụng", level=2)
    document.add_paragraph(
        "Attention giúp mô hình xử lý quan hệ xa trong chuỗi và hỗ trợ xử lý song song."
    )
    document.save(path)


def expect(response: httpx.Response, expected: int | tuple[int, ...]) -> dict:
    allowed = (expected,) if isinstance(expected, int) else expected
    if response.status_code not in allowed:
        raise RuntimeError(
            f"{response.request.method} {response.request.url} "
            f"returned {response.status_code}: {response.text[:1000]}"
        )
    if response.status_code == 204:
        return {}
    return response.json()


def sign_in(client: httpx.Client, email: str, password: str) -> str:
    payload = expect(
        client.post(
            "/auth/signin",
            json={"email": email, "password": password},
        ),
        200,
    )
    token = payload.get("access_token")
    if not token:
        raise RuntimeError("Sign-in returned no access token")
    return token


def create_project(client: httpx.Client) -> dict:
    stamp = int(time.time())
    return expect(
        client.post(
            "/projects",
            json={
                "name": f"E2E Smoke {stamp}",
                "description": "Temporary project created by smoke_e2e.py",
                "target_score": 80,
                "exam_date": None,
                "weekly_study_minutes": 300,
            },
        ),
        201,
    )


def upload_document(
    client: httpx.Client,
    project_id: str,
    path: Path,
) -> dict:
    with path.open("rb") as handle:
        return expect(
            client.post(
                f"/projects/{project_id}/documents",
                files={
                    "file": (
                        path.name,
                        handle,
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    )
                },
            ),
            202,
        )


def wait_for_job(
    client: httpx.Client,
    job_id: str,
    timeout_seconds: int,
) -> dict:
    deadline = time.monotonic() + timeout_seconds
    last: dict = {}

    while time.monotonic() < deadline:
        last = expect(client.get(f"/document-jobs/{job_id}"), 200)
        status = last.get("status")
        stage = last.get("stage")
        print(f"[ingest] status={status} stage={stage}")

        if status == "succeeded":
            return last
        if status in {"failed", "cancelled"}:
            raise RuntimeError(
                "Ingest did not succeed: "
                + json.dumps(last, ensure_ascii=False, indent=2)
            )
        time.sleep(2)

    raise TimeoutError(
        "Timed out waiting for ingest job. Last state: "
        + json.dumps(last, ensure_ascii=False)
    )


def verify_document_ready(
    client: httpx.Client,
    project_id: str,
    document_id: str,
) -> dict:
    detail = expect(
        client.get(f"/projects/{project_id}/documents/{document_id}"),
        200,
    )
    active_version_id = detail.get("active_version_id")
    if not active_version_id:
        raise RuntimeError("Document has no active_version_id after successful ingest")

    versions = detail.get("versions") or []
    active = next(
        (row for row in versions if row.get("id") == active_version_id),
        None,
    )
    if not active or active.get("status") != "ready":
        raise RuntimeError(
            "Active document version is not ready: "
            + json.dumps(active, ensure_ascii=False)
        )
    return detail


def cleanup_project(client: httpx.Client, project_id: str) -> None:
    response = client.delete(f"/projects/{project_id}")
    if response.status_code not in {204, 404}:
        raise RuntimeError(
            f"cleanup project returned {response.status_code}: "
            f"{response.text[:500]}"
        )


def run_chat(client: httpx.Client, project_id: str) -> dict:
    session = expect(
        client.post(f"/projects/{project_id}/chat/sessions"),
        201,
    )
    session_id = session["id"]

    answer = expect(
        client.post(
            f"/projects/{project_id}/chat/sessions/{session_id}/messages",
            json={
                "content": "Attention trong Transformer sử dụng ba vector nào?"
            },
        ),
        201,
    )

    content = str(answer.get("content") or "").casefold()
    if answer.get("role") != "assistant":
        raise RuntimeError("Chat response was not an assistant message")
    if not all(keyword in content for keyword in ("query", "key", "value")):
        raise RuntimeError(
            "Answer did not contain expected grounded concepts: "
            + str(answer.get("content"))
        )

    citations = answer.get("citations") or []
    if not citations:
        raise RuntimeError("Assistant answer did not include citations")

    return answer


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run RAGTutor backend vertical-slice smoke test."
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv(
            "RAGTUTOR_API_URL",
            "http://127.0.0.1:8000/api/v1",
        ),
    )
    parser.add_argument(
        "--email",
        default=os.getenv("RAGTUTOR_TEST_EMAIL", ""),
    )
    parser.add_argument(
        "--password",
        default=os.getenv("RAGTUTOR_TEST_PASSWORD", ""),
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=180,
        help="Maximum seconds to wait for Celery ingest.",
    )
    parser.add_argument(
        "--eval-output",
        type=Path,
        default=None,
        help="Optional path to write a fixed RAG evaluation result JSON.",
    )
    args = parser.parse_args()

    if not args.email or not args.password:
        raise SystemExit(
            "Provide --email/--password or RAGTUTOR_TEST_EMAIL/"
            "RAGTUTOR_TEST_PASSWORD. Do not commit credentials."
        )

    with httpx.Client(
        base_url=args.base_url.rstrip("/"),
        timeout=60,
    ) as client:
        token = sign_in(client, args.email, args.password)
        client.headers["Authorization"] = f"Bearer {token}"

        me = expect(client.get("/auth/me"), 200)
        print(f"[auth] signed in as {me.get('email')}")

        project = create_project(client)
        project_id = project["id"]
        print(f"[project] created {project_id}")

        try:
            with tempfile.TemporaryDirectory(prefix="ragtutor-e2e-") as temp_dir:
                path = Path(temp_dir) / "transformer_attention_smoke.docx"
                make_docx(path)

                upload = upload_document(client, project_id, path)
                document_id = upload["document_id"]
                job_id = upload["job_id"]
                print(f"[upload] document={document_id} job={job_id}")

                wait_for_job(client, job_id, args.timeout)
                detail = verify_document_ready(
                    client,
                    project_id,
                    document_id,
                )
                print(
                    "[document] ready active_version="
                    + str(detail["active_version_id"])
                )

                answer = run_chat(client, project_id)
                print(
                    "[rag] citation_count="
                    + str(len(answer.get("citations") or []))
                )

            print(
                json.dumps(
                    {
                        "status": "PASS",
                        "project_id": project_id,
                        "document_id": document_id,
                        "job_id": job_id,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
        finally:
            cleanup_project(client, project_id)
            print(f"[cleanup] deleted temporary project {project_id}")


if __name__ == "__main__":
    main()
