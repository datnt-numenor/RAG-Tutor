from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass

import httpx


@dataclass
class Actor:
    email: str
    token: str
    client: httpx.Client


def expect(
    response: httpx.Response,
    expected: int | tuple[int, ...],
    label: str,
) -> dict | list:
    allowed = (expected,) if isinstance(expected, int) else expected
    if response.status_code not in allowed:
        raise RuntimeError(
            f"{label}: expected {allowed}, got {response.status_code}: "
            f"{response.text[:1000]}"
        )
    if response.status_code == 204:
        return {}
    return response.json()


def login(
    base_url: str,
    email: str,
    password: str,
) -> Actor:
    client = httpx.Client(
        base_url=base_url.rstrip("/"),
        timeout=30,
    )
    result = expect(
        client.post(
            "/auth/signin",
            json={"email": email, "password": password},
        ),
        200,
        f"signin {email}",
    )
    token = result.get("access_token")
    if not token:
        raise RuntimeError(f"No access token returned for {email}")
    client.headers["Authorization"] = f"Bearer {token}"
    return Actor(email=email, token=token, client=client)


def create_project(actor: Actor, suffix: str) -> dict:
    return expect(
        actor.client.post(
            "/projects",
            json={
                "name": f"Security E2E {suffix}",
                "description": "Temporary authorization test project",
                "target_score": 80,
                "exam_date": None,
                "weekly_study_minutes": 120,
            },
        ),
        201,
        f"{actor.email} create project",
    )


def cleanup_project(actor: Actor, project_id: str | None) -> None:
    if not project_id:
        return
    response = actor.client.delete(f"/projects/{project_id}")
    if response.status_code not in {204, 404}:
        print(
            f"[WARN] cleanup {project_id} returned "
            f"{response.status_code}: {response.text[:300]}"
        )


def supabase_rest_visible(
    supabase_url: str,
    anon_key: str,
    actor: Actor,
    project_id: str,
) -> bool:
    response = httpx.get(
        f"{supabase_url.rstrip('/')}/rest/v1/projects",
        params={
            "select": "id",
            "id": f"eq.{project_id}",
        },
        headers={
            "apikey": anon_key,
            "Authorization": f"Bearer {actor.token}",
        },
        timeout=20,
    )
    if response.status_code != 200:
        raise RuntimeError(
            f"Direct Supabase RLS request failed: "
            f"{response.status_code} {response.text[:500]}"
        )
    rows = response.json()
    return any(row.get("id") == project_id for row in rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="RAGTutor two-user authorization integration test."
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv(
            "RAGTUTOR_API_URL",
            "http://127.0.0.1:8000/api/v1",
        ),
    )
    parser.add_argument(
        "--owner-email",
        default=os.getenv("RAGTUTOR_OWNER_EMAIL", ""),
    )
    parser.add_argument(
        "--owner-password",
        default=os.getenv("RAGTUTOR_OWNER_PASSWORD", ""),
    )
    parser.add_argument(
        "--member-email",
        default=os.getenv("RAGTUTOR_MEMBER_EMAIL", ""),
    )
    parser.add_argument(
        "--member-password",
        default=os.getenv("RAGTUTOR_MEMBER_PASSWORD", ""),
    )
    parser.add_argument(
        "--supabase-url",
        default=os.getenv("SUPABASE_URL", ""),
    )
    parser.add_argument(
        "--supabase-anon-key",
        default=os.getenv("SUPABASE_ANON_KEY", ""),
    )
    args = parser.parse_args()

    required = {
        "owner email": args.owner_email,
        "owner password": args.owner_password,
        "member email": args.member_email,
        "member password": args.member_password,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise SystemExit(
            "Missing credentials: " + ", ".join(missing)
        )
    if args.owner_email.casefold() == args.member_email.casefold():
        raise SystemExit("Owner and member must be different accounts")

    owner = login(
        args.base_url,
        args.owner_email,
        args.owner_password,
    )
    member = login(
        args.base_url,
        args.member_email,
        args.member_password,
    )

    owner_project_id: str | None = None
    member_project_id: str | None = None

    try:
        owner_project = create_project(owner, "owner")
        member_project = create_project(member, "member")
        owner_project_id = owner_project["id"]
        member_project_id = member_project["id"]

        # Cross-project FastAPI isolation before invitation.
        expect(
            owner.client.get(f"/projects/{member_project_id}"),
            404,
            "owner cannot read member project",
        )
        expect(
            member.client.get(f"/projects/{owner_project_id}"),
            404,
            "member cannot read owner project before invite",
        )

        # Direct Supabase RLS should enforce the same isolation when configured.
        if args.supabase_url and args.supabase_anon_key:
            if supabase_rest_visible(
                args.supabase_url,
                args.supabase_anon_key,
                owner,
                member_project_id,
            ):
                raise RuntimeError(
                    "RLS leak: owner account can directly read member project"
                )
            if supabase_rest_visible(
                args.supabase_url,
                args.supabase_anon_key,
                member,
                owner_project_id,
            ):
                raise RuntimeError(
                    "RLS leak: member account can directly read owner project"
                )
            print("[PASS] direct Supabase RLS cross-project isolation")

        # Owner invites second account.
        invitation = expect(
            owner.client.post(
                f"/projects/{owner_project_id}/invitations",
                json={"email": args.member_email},
            ),
            201,
            "create invitation",
        )
        invite_link = str(invitation["invite_link"])
        raw_token = invite_link.rstrip("/").split("/")[-1]

        expect(
            member.client.post(
                f"/invitations/{raw_token}/accept"
            ),
            201,
            "member accepts invitation",
        )

        # Member can now read shared project and create personal chat.
        expect(
            member.client.get(f"/projects/{owner_project_id}"),
            200,
            "member reads shared project",
        )
        session = expect(
            member.client.post(
                f"/projects/{owner_project_id}/chat/sessions"
            ),
            201,
            "member creates chat session",
        )

        # Member cannot perform owner-only content management.
        expect(
            member.client.post(
                f"/projects/{owner_project_id}/documents",
                files={
                    "file": (
                        "fake.pdf",
                        b"%PDF-1.4\n%%EOF",
                        "application/pdf",
                    )
                },
            ),
            403,
            "member cannot upload project document",
        )
        expect(
            member.client.get(
                f"/projects/{owner_project_id}/invitations"
            ),
            403,
            "member cannot manage invitations",
        )

        # Owner removes member.
        expect(
            owner.client.delete(
                f"/projects/{owner_project_id}/members/"
                f"{expect(member.client.get('/auth/me'), 200, 'member me')['user_id']}"
            ),
            204,
            "owner removes member",
        )

        # Access must be revoked immediately, including old chat sessions.
        expect(
            member.client.get(f"/projects/{owner_project_id}"),
            404,
            "removed member cannot read project",
        )
        expect(
            member.client.get(
                f"/projects/{owner_project_id}/chat/sessions"
            ),
            404,
            "removed member cannot list old chat sessions",
        )
        expect(
            member.client.get(
                f"/projects/{owner_project_id}/chat/sessions/"
                f"{session['id']}/messages"
            ),
            404,
            "removed member cannot read old chat history",
        )

        if args.supabase_url and args.supabase_anon_key:
            if supabase_rest_visible(
                args.supabase_url,
                args.supabase_anon_key,
                member,
                owner_project_id,
            ):
                raise RuntimeError(
                    "RLS leak after removal: removed member still sees project"
                )
            print("[PASS] direct Supabase RLS revokes access after removal")

        print(
            json.dumps(
                {
                    "status": "PASS",
                    "owner_project_id": owner_project_id,
                    "member_project_id": member_project_id,
                    "checks": [
                        "FastAPI cross-project isolation",
                        "invitation accept",
                        "member read access",
                        "owner-only document management",
                        "owner-only invitation management",
                        "membership revocation",
                        "old chat access revocation",
                        "direct Supabase RLS when env supplied",
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    finally:
        cleanup_project(owner, owner_project_id)
        cleanup_project(member, member_project_id)
        owner.client.close()
        member.client.close()


if __name__ == "__main__":
    main()
