"""Interactive local bootstrap; run: python -m app.scripts.create_user --username ... --role ..."""

import argparse
from getpass import getpass

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.security import hash_password
from app.db.session import get_session_factory
from app.models import User


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a local admin/operator account")
    parser.add_argument("--username", required=True)
    parser.add_argument("--role", choices=["admin", "operator"], required=True)
    args = parser.parse_args()
    username = args.username.strip()
    if not 1 <= len(username) <= 80:
        parser.error("Username length must be 1–80 characters")

    password = getpass("Password (minimum 12 characters): ")
    repeat = getpass("Confirm password: ")
    if password != repeat:
        parser.error("Passwords do not match")
    if not 12 <= len(password) <= 128:
        parser.error("Password length must be 12–128 characters")

    with get_session_factory()() as db:
        if db.scalar(select(User.id).where(User.username == username)) is not None:
            parser.error("Username already exists; no user was changed")
        db.add(User(username=username, role=args.role, password_hash=hash_password(password)))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            parser.error("Username conflict; no user was changed")
    print(f"Created account {username!r} with role {args.role!r}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
