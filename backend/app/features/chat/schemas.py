from typing import Self

from pydantic import BaseModel, Field, model_validator

from app.llm.types import ChatMessage, GenerationOptions, ModelInfo

MAX_MESSAGES = 200


class ChatRequest(BaseModel):
    # None means "use the server default" (CHAT_MODEL, TEMPERATURE and NUM_CTX from .env).
    model: str | None = Field(default=None, min_length=1, max_length=200)
    messages: list[ChatMessage] = Field(min_length=1, max_length=MAX_MESSAGES)
    options: GenerationOptions | None = None

    @model_validator(mode="after")
    def last_message_must_come_from_the_user(self) -> Self:
        if self.messages[-1].role != "user":
            raise ValueError("The last message must have role 'user'.")
        return self


class ModelsResponse(BaseModel):
    models: list[ModelInfo]
    default_chat_model: str
