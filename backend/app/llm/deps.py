from typing import Annotated

from fastapi import Depends, Request

from app.core.config import Settings, get_settings
from app.llm.provider import LLMProvider


def get_provider(request: Request) -> LLMProvider:
    """Return the provider created at startup (see the lifespan in app/main.py).

    Tests replace this function through app.dependency_overrides to inject a FakeProvider.
    """
    provider: LLMProvider = request.app.state.provider
    return provider


ProviderDep = Annotated[LLMProvider, Depends(get_provider)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
