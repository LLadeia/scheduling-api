from fastapi import HTTPException


class DomainError(HTTPException):
    def __init__(self, status: int, detail: str):
        super().__init__(status_code=status, detail=detail)


def unauthorized() -> HTTPException:
    return HTTPException(
        401, "Credenciais ou token inválidos", headers={"WWW-Authenticate": "Bearer"}
    )
