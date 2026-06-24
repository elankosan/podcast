"""Bootstrap the first admin user for a fresh deployment.

Usage:
  python bootstrap_admin.py --email admin@example.com --name Admin --password 'strong-pass'

The command is idempotent:
- If the user exists, it updates role to admin.
- If no user exists, it creates the first admin.
"""

import argparse

from sqlalchemy.orm import Session

from api.auth import get_password_hash
from api.database import SessionLocal
from api.models.user import User


def bootstrap_admin(db: Session, email: str, name: str, password: str) -> str:
    user = db.query(User).filter(User.email == email).first()

    if user:
        user.role = "admin"
        if password:
            user.hashed_password = get_password_hash(password)
        if name:
            user.name = name
        db.commit()
        return f"Updated existing user {email} and granted admin role"

    user_count = db.query(User).count()
    if user_count > 0:
        return (
            "Refused to create new admin: users already exist. "
            "Create admin via /api/admin/users using an existing admin token."
        )

    admin = User(
        email=email,
        name=name,
        hashed_password=get_password_hash(password),
        role="admin",
    )
    db.add(admin)
    db.commit()
    return f"Created initial admin user {email}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap initial admin user")
    parser.add_argument("--email", required=True, help="Admin email")
    parser.add_argument("--name", required=True, help="Admin display name")
    parser.add_argument("--password", required=True, help="Admin password")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        message = bootstrap_admin(db, args.email, args.name, args.password)
        print(message)
    finally:
        db.close()


if __name__ == "__main__":
    main()
