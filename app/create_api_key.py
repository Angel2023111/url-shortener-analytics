
import argparse
import sys

from sqlalchemy.orm import Session

from app.api_key_models import APIKey
from app.api_keys import generate_api_key, hash_api_key
from app.database import SessionLocal, engine


def create_api_key(name: str) -> str:
    # Create only the API key table if it does not exist.
    APIKey.__table__.create(bind=engine, checkfirst=True)

    raw_key = generate_api_key()

    with SessionLocal() as db:
        api_key = APIKey(
            key_hash=hash_api_key(raw_key),
            name=name,
            is_active=True,
        )
        db.add(api_key)
        db.commit()

    return raw_key


def main():
    parser = argparse.ArgumentParser(
        description="Create an API key for the URL Shortener API."
    )
    parser.add_argument(
        "--name",
        required=True,
        help="Descriptive name for the API key.",
    )
    args = parser.parse_args()

    name = args.name.strip()
    if not name or len(name) > 100:
        parser.error("--name must contain between 1 and 100 characters.")

    try:
        raw_key = create_api_key(name)
    except Exception:
        print(
            "Failed to create API key. Check database connectivity "
            "and permissions.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    print("API key created successfully.")
    print(f"Name: {name}")
    print("Copy this key now; it will not be displayed again:")
    print(raw_key)


if __name__ == "__main__":
    main()
