import pytest
from pydantic import ValidationError

from app.llm import GenerationOptions, GenerationStats


def test_tokens_per_second_divides_output_tokens_by_generation_time() -> None:
    stats = GenerationStats(output_tokens=90, generation_seconds=2.5)

    assert stats.tokens_per_second == pytest.approx(36.0)


def test_tokens_per_second_is_zero_when_no_time_was_measured() -> None:
    stats = GenerationStats(output_tokens=10, generation_seconds=0.0)

    assert stats.tokens_per_second == 0.0


def test_tokens_per_second_is_included_when_serialized() -> None:
    stats = GenerationStats(output_tokens=10, generation_seconds=2.0)

    assert stats.model_dump()["tokens_per_second"] == pytest.approx(5.0)


@pytest.mark.parametrize(
    "invalid",
    [{"temperature": -0.1}, {"temperature": 2.5}, {"num_ctx": 0}, {"max_tokens": 0}],
)
def test_options_reject_out_of_range_values(invalid: dict[str, float]) -> None:
    with pytest.raises(ValidationError):
        GenerationOptions(**invalid)  # type: ignore[arg-type]
