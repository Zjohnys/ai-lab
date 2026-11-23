import tomllib
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, Field, model_validator

from app.llm.types import ChatMessage, GenerationOptions

DATA_DIR = Path(__file__).resolve().parent / "data"


class EvalCase(BaseModel):
    id: str = Field(min_length=1)
    message: str = Field(min_length=1)
    expected: str
    difficulty: Literal["easy", "hard"] = "easy"
    note: str | None = None


class EvalDataset(BaseModel):
    name: str
    description: str = ""
    labels: list[str] = Field(min_length=2)
    cases: list[EvalCase] = Field(min_length=1)

    @model_validator(mode="after")
    def check_consistency(self) -> Self:
        ids = [case.id for case in self.cases]
        duplicates = {case_id for case_id in ids if ids.count(case_id) > 1}
        if duplicates:
            raise ValueError(f"Duplicate case ids: {sorted(duplicates)}")
        unknown = {case.expected for case in self.cases} - set(self.labels)
        if unknown:
            raise ValueError(f"Expected labels not in the label list: {sorted(unknown)}")
        return self


class PromptVersion(BaseModel):
    id: str = Field(min_length=1)
    description: str = ""
    system: str = ""
    user_template: str

    @model_validator(mode="after")
    def template_must_include_the_message(self) -> Self:
        if "{message}" not in self.user_template:
            raise ValueError(f"Prompt '{self.id}': user_template must contain {{message}}.")
        return self

    def render(self, message: str, labels: list[str]) -> list[ChatMessage]:
        """Fill the placeholders with str.replace: JSON examples with braces stay intact."""
        label_text = ", ".join(labels)

        def fill(text: str) -> str:
            return text.replace("{labels}", label_text).replace("{message}", message)

        messages: list[ChatMessage] = []
        if self.system.strip():
            messages.append(ChatMessage(role="system", content=fill(self.system)))
        messages.append(ChatMessage(role="user", content=fill(self.user_template)))
        return messages


class _PromptFile(BaseModel):
    versions: list[PromptVersion] = Field(min_length=1)


def load_dataset(path: Path) -> EvalDataset:
    return EvalDataset.model_validate_json(path.read_text(encoding="utf-8"))


def load_prompts(path: Path) -> list[PromptVersion]:
    with path.open("rb") as file:
        versions = _PromptFile.model_validate(tomllib.load(file)).versions
    ids = [version.id for version in versions]
    if len(ids) != len(set(ids)):
        raise ValueError(f"Duplicate prompt ids in {path.name}: {ids}")
    return versions


# --- Results ---------------------------------------------------------------------------------


class CaseResult(BaseModel):
    case_id: str
    expected: str
    predicted: str | None
    correct: bool
    strict_json: bool
    json_found: bool
    label_valid: bool
    raw_output: str
    error: str | None = None
    latency_seconds: float
    output_tokens: int = 0
    tokens_per_second: float = 0.0


class LabelScore(BaseModel):
    total: int
    correct: int


class EvalSummary(BaseModel):
    total: int
    correct: int
    accuracy: float
    strict_json_rate: float
    json_found_rate: float
    valid_label_rate: float
    errors: int
    mean_latency_seconds: float
    max_latency_seconds: float
    mean_tokens_per_second: float
    per_label: dict[str, LabelScore]


class EvalRun(BaseModel):
    dataset: str
    prompt_id: str
    model: str
    options: GenerationOptions
    started_at: str
    summary: EvalSummary
    results: list[CaseResult]
