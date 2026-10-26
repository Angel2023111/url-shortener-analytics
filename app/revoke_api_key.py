
import getpass

from sqlalchemy import select

from app.api_key_models import APIKey
from app.api_keys import hash_api_key
from app.database import SessionLocal


def main() -> None:
    raw_key = getpass.getpass("Enter the API key to revoke (input hidden): ")

    if not raw_key:
        print("No API key provided.")
        return

    key_hash = hash_api_key(raw_key)

    with SessionLocal() as db:
        api_key = db.scalar(
            select(APIKey).where(APIKey.key_hash == key_hash)
        )

        if api_key is None:
            print("API key not found.")
            return

        if not api_key.is_active:
            print(f"API key '{api_key.name}' is already inactive.")
            return

        api_key.is_active = False
        db.commit()
        print(f"API key '{api_key.name}' has been deactivated.")


if __name__ == "__main__":
    main()
