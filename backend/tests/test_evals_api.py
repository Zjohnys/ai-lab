"""Evaluation API tests with FakeProvider: no Ollama, no model."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.llm import LLMProvider, ModelNotFoundError, ProviderUnavailableError
from app.llm.deps import get_provider
from app.llm.fake import FakeProvider
from app.main import app


@pytest.fixture(autouse=True)
def clean_overrides() -> Iterator[None]:
    app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None)
    yield
    app.dependency_overrides.clear()


def client_with(provider: LLMProvider) -> TestClient:
    app.dependency_overrides[get_provider] = lambda: provider
    return TestClient(app)


def test_datasets_lists_both_sets_with_their_prompts() -> None:
    response = client_with(FakeProvider()).get("/api/evals/datasets")

    assert response.status_code == 200
    by_name = {dataset["name"]: dataset for dataset in response.json()}
    assert by_name["support_triage"]["cases"] == 15
    assert by_name["support_triage_holdout"]["cases"] == 10
    for dataset in by_name.values():
        assert [p["id"] for p in dataset["prompts"]] == [
            "v1_basic",
            "v2_definitions",
            "v3_few_shot",
        ]


def test_run_scores_the_dataset_and_uses_the_default_model() -> None:
    # Always answering "rede" gets exactly the 3 rede cases right.
    provider = FakeProvider(reply='{"category": "rede"}')

    response = client_with(provider).post(
        "/api/evals/run", json={"dataset": "support_triage", "prompt_id": "v2_definitions"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["model"] == "qwen3:8b"
    assert body["prompt_id"] == "v2_definitions"
    assert body["summary"]["total"] == 15
    assert body["summary"]["correct"] == 3
    assert body["summary"]["strict_json_rate"] == 1.0
    assert len(provider.calls) == 15
    assert provider.calls[0].options.temperature == 0.0


def test_run_uses_the_requested_model() -> None:
    provider = FakeProvider(reply='{"category": "rede"}')

    client_with(provider).post(
        "/api/evals/run",
        json={"dataset": "support_triage_holdout", "prompt_id": "v1_basic", "model": "qwen3:4b"},
    )

    assert {call.model for call in provider.calls} == {"qwen3:4b"}
    assert len(provider.calls) == 10


@pytest.mark.parametrize("dataset", ["nao-existe", "../../.env", "support_triage_prompts"])
def test_unknown_or_unsafe_dataset_names_are_not_found(dataset: str) -> None:
    provider = FakeProvider()

    response = client_with(provider).post(
        "/api/evals/run", json={"dataset": dataset, "prompt_id": "v1_basic"}
    )

    assert response.status_code == 404
    assert provider.calls == []


def test_unknown_prompt_is_not_found() -> None:
    response = client_with(FakeProvider()).post(
        "/api/evals/run", json={"dataset": "support_triage", "prompt_id": "v9"}
    )

    assert response.status_code == 404
    assert "v9" in response.json()["detail"]


@pytest.mark.parametrize(
    ("error", "expected_status"),
    [(ModelNotFoundError("not installed"), 404), (ProviderUnavailableError("down"), 503)],
)
def test_provider_failures_stop_the_run_with_an_http_error(
    error: Exception, expected_status: int
) -> None:
    provider = FakeProvider(fail_with=error)  # type: ignore[arg-type]

    response = client_with(provider).post("/api/evals/run", json={"prompt_id": "v1_basic"})

    assert response.status_code == expected_status
    assert len(provider.calls) == 1  # stopped at the first case, not 15 failures


def test_run_defaults_to_thinking_off_and_a_short_answer() -> None:
    provider = FakeProvider(reply='{"category": "rede"}')

    client_with(provider).post("/api/evals/run", json={"prompt_id": "v1_basic"})

    assert provider.calls[0].options.think is False
    assert provider.calls[0].options.max_tokens == 64


def test_run_passes_thinking_and_token_budget() -> None:
    provider = FakeProvider(reply='{"category": "rede"}')

    client_with(provider).post(
        "/api/evals/run",
        json={"prompt_id": "v1_basic", "model": "qwen3:4b", "think": True, "max_tokens": 2048},
    )

    options = provider.calls[0].options
    assert (options.think, options.max_tokens, options.temperature) == (True, 2048, 0.0)


@pytest.mark.parametrize("max_tokens", [0, 5000])
def test_run_rejects_a_token_budget_out_of_range(max_tokens: int) -> None:
    response = client_with(FakeProvider()).post(
        "/api/evals/run", json={"prompt_id": "v1_basic", "max_tokens": max_tokens}
    )

    assert response.status_code == 422


def test_run_requires_a_prompt_id() -> None:
    response = client_with(FakeProvider()).post("/api/evals/run", json={})

    assert response.status_code == 422
