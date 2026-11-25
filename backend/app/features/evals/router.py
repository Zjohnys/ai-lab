from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.features.evals.runner import DEFAULT_EVAL_OPTIONS, run_eval
from app.features.evals.schemas import (
    EvalDataset,
    EvalRun,
    PromptVersion,
    available_datasets,
    load_dataset,
    prompts_for,
)
from app.llm.deps import ProviderDep, SettingsDep
from app.llm.http_errors import to_http_error
from app.llm.provider import LLMProviderError

router = APIRouter(prefix="/api/evals", tags=["evals"])


class PromptSummary(BaseModel):
    id: str
    description: str


class DatasetSummary(BaseModel):
    name: str
    description: str
    labels: list[str]
    cases: int
    prompts: list[PromptSummary]


class EvalRequest(BaseModel):
    dataset: str = Field(default="support_triage", min_length=1, max_length=100)
    prompt_id: str = Field(min_length=1, max_length=100)
    model: str | None = Field(default=None, min_length=1, max_length=200)


def _find_dataset(name: str) -> tuple[EvalDataset, list[PromptVersion]]:
    # The name is only used as a dictionary key: "../../.env" simply is not found.
    path = available_datasets().get(name)
    if path is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown dataset '{name}'.")
    dataset = load_dataset(path)
    return dataset, prompts_for(dataset)


@router.get("/datasets")
def list_datasets() -> list[DatasetSummary]:
    summaries: list[DatasetSummary] = []
    for name in available_datasets():
        dataset, prompts = _find_dataset(name)
        summaries.append(
            DatasetSummary(
                name=dataset.name,
                description=dataset.description,
                labels=dataset.labels,
                cases=len(dataset.cases),
                prompts=[PromptSummary(id=p.id, description=p.description) for p in prompts],
            )
        )
    return summaries


@router.post(
    "/run",
    responses={
        404: {"description": "Unknown dataset or prompt, or the model is not installed."},
        502: {"description": "The provider failed."},
        503: {"description": "The provider is not running."},
    },
)
async def run(request: EvalRequest, provider: ProviderDep, settings: SettingsDep) -> EvalRun:
    """Run one prompt version on every case of a dataset. Takes seconds to minutes."""
    dataset, prompts = _find_dataset(request.dataset)
    prompt = next((p for p in prompts if p.id == request.prompt_id), None)
    if prompt is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            f"Unknown prompt '{request.prompt_id}' for dataset '{dataset.name}'.",
        )
    try:
        return await run_eval(
            provider, request.model or settings.chat_model, dataset, prompt, DEFAULT_EVAL_OPTIONS
        )
    except LLMProviderError as exc:
        raise to_http_error(exc) from exc
