from fastapi import HTTPException, status

from app.llm.provider import LLMProviderError, ModelNotFoundError, ProviderUnavailableError


def to_http_error(exc: LLMProviderError) -> HTTPException:
    """Map provider failures to HTTP status codes, the same way for every endpoint."""
    if isinstance(exc, ModelNotFoundError):
        return HTTPException(status.HTTP_404_NOT_FOUND, str(exc))
    if isinstance(exc, ProviderUnavailableError):
        return HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc))
    return HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc))
