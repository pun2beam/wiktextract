import json
from pathlib import Path

from wiktextract.rest_parser import parse_mobile_html


def _load_fixture() -> str:
    return Path("tests/data/lay_minimal_rest.html").read_text(encoding="utf-8")


def _extract_examples(entry: dict) -> list[str]:
    examples: list[str] = []
    for sense in entry.get("senses", []):
        for example in sense.get("examples", []) or []:
            text = example.get("text")
            if text:
                examples.append(text)
    return examples


def test_lay_example_attaches_to_verb_only():
    html_text = _load_fixture()
    data = parse_mobile_html("lay", html_text)

    verb_entry = next(item for item in data if item.get("pos") == "verb")
    noun_entry = next(item for item in data if item.get("pos") == "noun")

    verb_examples = _extract_examples(verb_entry)
    noun_examples = _extract_examples(noun_entry)

    assert any(
        "I never kill a pullet" in example for example in verb_examples
    ), verb_examples
    assert not any(
        "I never kill a pullet" in example for example in noun_examples
    ), noun_examples
