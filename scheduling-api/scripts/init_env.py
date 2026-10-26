"""Local-only configuration generator. Never overwrites an existing .env."""

from pathlib import Path
from secrets import token_urlsafe


def main():
    path = Path(".env")
    password, secret = token_urlsafe(24), token_urlsafe(48)
    content = f"POSTGRES_USER=scheduling\nPOSTGRES_DB=scheduling\nPOSTGRES_PASSWORD={password}\nDATABASE_URL=postgresql+asyncpg://scheduling:{password}@db:5432/scheduling\nJWT_SECRET={secret}\n"
    with path.open("x") as file:
        file.write(content)
    path.chmod(0o600)
    print(".env criado. Segredos não serão exibidos.")


if __name__ == "__main__":
    main()
