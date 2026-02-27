from typing import Any


class BusinessError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        detail: Any = None,
        status_code: int = 400,
    ):
        self.code = code
        self.message = message
        self.detail = detail
        self.status_code = status_code
        super().__init__(message)
