from typing import Literal

from pydantic import BaseModel, Field, computed_field

Role = Literal["system", "user", "assistant"]


class ChatMessage(BaseModel):
    role: Role
    content: str


class GenerationOptions(BaseModel):
    """Sampling and context parameters, independent of any provider's naming."""

    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    # Context window in tokens. Capped at 32768: far more than fits in 8 GB of VRAM.
    num_ctx: int = Field(default=8192, ge=256, le=32768)
    max_tokens: int | None = Field(default=None, ge=1)
    seed: int | None = None
    think: bool = False


class GenerationStats(BaseModel):
    """Counters reported by the provider when a generation finishes."""

    prompt_tokens: int = 0
    output_tokens: int = 0
    load_seconds: float = 0.0
    prompt_eval_seconds: float = 0.0
    generation_seconds: float = 0.0
    total_seconds: float = 0.0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def tokens_per_second(self) -> float:
        if self.generation_seconds <= 0:
            return 0.0
        return self.output_tokens / self.generation_seconds


class ChatChunk(BaseModel):
    """One piece of a streamed answer. The last chunk has done=True and carries the stats."""

    content: str = ""
    thinking: str = ""
    done: bool = False
    stats: GenerationStats | None = None


class ModelInfo(BaseModel):
    name: str
    size_bytes: int
    parameter_size: str | None = None
    quantization: str | None = None
