import argparse
import asyncio
from getpass import getpass

from pydantic import ValidationError

from app.db.session import SessionLocal, engine
from app.schemas.contracts import Register
from app.services.auth import register


async def create(email, password):
    try:
        async with SessionLocal() as session:
            user = await register(session, Register(email=email, password=password), role="admin")
            print(f"Admin criado: id={user.id}")
    finally:
        await engine.dispose()


def main():
    parser = argparse.ArgumentParser(
        description="Cria administrador com senha via entrada protegida"
    )
    parser.add_argument("--email", required=True)
    args = parser.parse_args()
    password = getpass("Senha (mínimo 12 caracteres): ")
    if password != getpass("Confirme a senha: "):
        raise SystemExit("Senhas diferentes")
    try:
        Register(email=args.email, password=password)
    except ValidationError:
        raise SystemExit(
            "E-mail inválido ou senha com menos de 12 ou mais de 128 caracteres"
        ) from None
    asyncio.run(create(args.email, password))


if __name__ == "__main__":
    main()
