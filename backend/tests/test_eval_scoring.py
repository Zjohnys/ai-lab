import pytest

from app.features.evals.scoring import normalize_label, parse_output

LABELS = ["acesso", "hardware", "rede", "software", "seguranca"]


def test_exact_json_is_strict_and_valid() -> None:
    parsed = parse_output('{"category": "rede"}', LABELS)

    assert (parsed.strict_json, parsed.json_found, parsed.label, parsed.label_valid) == (
        True,
        True,
        "rede",
        True,
    )


def test_surrounding_whitespace_still_counts_as_strict() -> None:
    assert parse_output('\n  {"category": "rede"}  \n', LABELS).strict_json is True


@pytest.mark.parametrize(
    "text",
    [
        '```json\n{"category": "hardware"}\n```',
        '```\n{"category": "hardware"}\n```',
        'Claro! A categoria é:\n{"category": "hardware"}',
        '{"category": "hardware"}\nEssa é a categoria porque o teclado molhou.',
    ],
)
def test_json_wrapped_in_text_is_found_but_not_strict(text: str) -> None:
    parsed = parse_output(text, LABELS)

    assert parsed.strict_json is False
    assert parsed.json_found is True
    assert parsed.label == "hardware"


def test_accents_and_case_are_normalized() -> None:
    parsed = parse_output('{"category": "Segurança"}', LABELS)

    assert parsed.strict_json is True
    assert parsed.label == "seguranca"
    assert parsed.label_valid is True


def test_unknown_category_is_parsed_but_not_valid() -> None:
    parsed = parse_output('{"category": "email"}', LABELS)

    assert parsed.json_found is True
    assert parsed.label == "email"
    assert parsed.label_valid is False


@pytest.mark.parametrize(
    "text",
    [
        "rede",
        "A categoria é rede.",
        '{"category": rede}',
        '{"categoria": "rede"}',
        '{"category": ["rede"]}',
        '["rede"]',
        "",
    ],
)
def test_answers_without_a_usable_json_object_have_no_label(text: str) -> None:
    parsed = parse_output(text, LABELS)

    assert parsed.json_found is False
    assert parsed.label is None
    assert parsed.label_valid is False


def test_the_first_usable_object_wins() -> None:
    text = 'Exemplo: {"x": 1}. Resposta: {"category": "software"} ou {"category": "rede"}'

    assert parse_output(text, LABELS).label == "software"


def test_normalize_label() -> None:
    assert normalize_label("  SEGURANÇA ") == "seguranca"
    assert normalize_label("Acesso") == "acesso"
