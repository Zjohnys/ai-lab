"""Checks on the dataset and prompt files themselves: a broken gold label breaks every metric."""

from collections import Counter

import pytest
from pydantic import ValidationError

from app.features.evals.schemas import (
    DATA_DIR,
    EvalDataset,
    PromptVersion,
    load_dataset,
    load_prompts,
)

DATASET = load_dataset(DATA_DIR / "support_triage.json")
PROMPTS = load_prompts(DATA_DIR / "support_triage_prompts.toml")


def test_dataset_has_15_cases_balanced_across_5_labels() -> None:
    assert len(DATASET.cases) == 15
    assert Counter(case.expected for case in DATASET.cases) == {
        label: 3 for label in DATASET.labels
    }


def test_every_label_has_exactly_one_hard_case_with_a_note() -> None:
    hard = [case for case in DATASET.cases if case.difficulty == "hard"]

    assert sorted(case.expected for case in hard) == sorted(DATASET.labels)
    assert all(case.note for case in hard)


def test_labels_have_no_accents_or_uppercase() -> None:
    assert all(label == label.lower() and label.isascii() for label in DATASET.labels)


def test_there_are_three_prompt_versions() -> None:
    assert [prompt.id for prompt in PROMPTS] == ["v1_basic", "v2_definitions", "v3_few_shot"]


@pytest.mark.parametrize("prompt", PROMPTS, ids=lambda prompt: prompt.id)
def test_rendered_prompt_has_the_message_and_no_leftover_placeholders(
    prompt: PromptVersion,
) -> None:
    messages = prompt.render("Minha impressora não imprime.", DATASET.labels)
    text = "\n".join(message.content for message in messages)

    assert messages[-1].role == "user"
    assert "Minha impressora não imprime." in messages[-1].content
    assert "{message}" not in text
    assert "{labels}" not in text
    assert '{"category"' in text  # JSON braces survive rendering
    for label in DATASET.labels:
        assert label in text


def test_few_shot_examples_do_not_leak_dataset_cases() -> None:
    """An example copied from the test set would inflate the accuracy of v3."""
    few_shot = next(prompt for prompt in PROMPTS if prompt.id == "v3_few_shot")

    for case in DATASET.cases:
        assert case.message not in few_shot.system


def test_dataset_rejects_an_expected_label_outside_the_label_list() -> None:
    with pytest.raises(ValidationError, match="not in the label list"):
        EvalDataset(
            name="x",
            labels=["a", "b"],
            cases=[{"id": "1", "message": "m", "expected": "c"}],  # type: ignore[list-item]
        )


def test_dataset_rejects_duplicate_ids() -> None:
    case = {"id": "1", "message": "m", "expected": "a"}
    with pytest.raises(ValidationError, match="Duplicate"):
        EvalDataset(name="x", labels=["a", "b"], cases=[case, case])  # type: ignore[list-item]


def test_prompt_without_message_placeholder_is_rejected() -> None:
    with pytest.raises(ValidationError, match="message"):
        PromptVersion(id="bad", user_template="Classifique.")
