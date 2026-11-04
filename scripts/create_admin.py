"""Create the initial KaamConnect administrator securely.

Usage (from the project root, with the virtual environment activated):

    python scripts/create_admin.py --email admin@example.com --full-name "Site Admin"

The password is always requested interactively with getpass and is never
accepted as a command-line argument, logged, or written to disk.
"""

import argparse
import getpass
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.security import (  # noqa: E402
    hash_password,
    validate_email_format,
    validate_password_strength,
)
from app.db.session import SessionLocal  # noqa: E402
from app.models.enums import UserRole  # noqa: E402
from app.repositories.users import UserRepository  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a KaamConnect administrator")
    parser.add_argument("--email", required=True, help="Administrator email address")
    parser.add_argument("--full-name", required=True, help="Administrator full name")
    parser.add_argument(
        "--promote",
        action="store_true",
        help="Promote the existing account with this email to administrator",
    )
    args = parser.parse_args()

    try:
        email = validate_email_format(args.email)
        name = args.full_name.strip()
        if len(name) < 2:
            raise ValueError("Full name must be at least 2 characters")
    except ValueError as exc:
        print(f"Invalid input: {exc}", file=sys.stderr)
        return 1

    password = getpass.getpass("Administrator password: ")
    confirm = getpass.getpass("Confirm administrator password: ")
    if password != confirm:
        print("Passwords do not match.", file=sys.stderr)
        return 1
    try:
        validate_password_strength(password)
    except ValueError as exc:
        print(f"Invalid password: {exc}", file=sys.stderr)
        return 1

    db = SessionLocal()
    try:
        users = UserRepository(db)
        existing = users.get_by_email(email)
        if existing is not None:
            if not args.promote:
                print(
                    "An account with this email already exists. "
                    "Re-run with --promote to make this account an administrator.",
                    file=sys.stderr,
                )
                return 1
            if existing.role == UserRole.ADMIN.value:
                print(f"Account is already an administrator: {existing.email}")
                return 0
            existing.role = UserRole.ADMIN.value
            db.commit()
            print(f"Promoted existing account to administrator: {existing.email}")
            return 0
        user = users.create(
            email=email,
            password_hash=hash_password(password),
            full_name=name,
            phone=None,
            role=UserRole.ADMIN.value,
        )
        db.commit()
        print(f"Administrator created: {user.email} (id={user.id})")
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
