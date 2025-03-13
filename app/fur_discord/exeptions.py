from app.core.typing import JSONObject


class UnauthorizedError(Exception):
    """A Exception raised when user is not authorized."""


class InvalidRequestError(Exception):
    """A Exception raised when a Request is not Valid."""


class RateLimitedError(Exception):
    """A Exception raised when a Request is not Valid."""

    def __init__(self, json: JSONObject, headers: dict[str, str]) -> None:
        self.json: JSONObject = json
        self.headers: dict[str, str] = headers
        self.message: str = json["message"]
        self.retry_after: int = json["retry_after"]
        super().__init__(self.message)


class ScopeMissingError(Exception):
    scope: str

    def __init__(self, scope: str) -> None:
        self.scope = scope
        super().__init__(self.scope)
