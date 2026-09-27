from __future__ import annotations

import argparse
import json
import os

from supabase import create_client


def get_admin():
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_SERVICE_KEY", "").strip()
    if not url or not key:
        raise SystemExit("SUPABASE_URL and SUPABASE_SERVICE_KEY are required")
    return create_client(url, key)


def create_user(email: str, password: str, full_name: str) -> dict:
    admin = get_admin()
    response = admin.auth.admin.create_user(
        {
            "email": email,
            "password": password,
            "email_confirm": True,
            "user_metadata": {"full_name": full_name},
        }
    )
    user = response.user
    if user is None:
        raise RuntimeError(f"Failed to create test user {email}")
    return {"id": str(user.id), "email": user.email}


def delete_user(user_id: str) -> None:
    admin = get_admin()
    admin.auth.admin.delete_user(user_id)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create/delete temporary Supabase Auth users for runtime E2E."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    create = sub.add_parser("create")
    create.add_argument("--email", required=True)
    create.add_argument("--password", required=True)
    create.add_argument("--full-name", default="RAGTutor E2E")

    delete = sub.add_parser("delete")
    delete.add_argument("--user-id", required=True)

    args = parser.parse_args()

    if args.command == "create":
        print(
            json.dumps(
                create_user(args.email, args.password, args.full_name),
                ensure_ascii=False,
            )
        )
    else:
        delete_user(args.user_id)
        print(json.dumps({"deleted": args.user_id}))


if __name__ == "__main__":
    main()
