#!/usr/bin/env python3
"""Reproduce the lay example assignment issue via two extraction paths."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Iterable, List

from wikitextprocessor import Wtp

from wiktextract.config import WiktionaryConfig
from wiktextract.rest_parser import parse_mobile_html
from wiktextract.wiktionary import parse_page
from wiktextract.wxr_context import WiktextractContext

WIKITEXT_SNIPPET = """\
==English==
===Etymology 1===
====Verb====
# To produce and deposit an egg or eggs.
#: I never kill a pullet but keep to lay the next year.
====Noun====
# Arrangement or relationship; layout.
"""

HTML_FIXTURE = Path(__file__).resolve().parents[1] / "tests" / "data" / "lay_minimal_rest.html"
REST_ENDPOINT = "https://en.wiktionary.org/api/rest_v1/page/mobile-html/{title}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate JSONL outputs for the word 'lay' via two extraction "
            "paths: direct wikitext parsing (A) and REST-style HTML parsing "
            "(B)."
        )
    )
    parser.add_argument("--word", default="lay", help="Entry title to process")
    parser.add_argument("--out-a", required=True, help="Path to write path A JSONL output")
    parser.add_argument("--out-b", required=True, help="Path to write path B JSONL output")
    parser.add_argument(
        "--contains",
        default=None,
        help=(
            "Optional substring to highlight in the produced outputs. The script"
            " prints entries whose example text contains this substring."
        ),
    )
    parser.add_argument(
        "--rest-html",
        default=None,
        help=(
            "Path to a local REST HTML fixture. Defaults to the bundled 'lay' "
            "fixture; otherwise, the script fetches live HTML from the "
            "Wiktionary REST API."
        ),
    )
    return parser.parse_args()


def run_path_a(word: str) -> List[dict]:
    if word != "lay":
        return []
    config = WiktionaryConfig()
    config.capture_language_codes = ["en"]
    config.capture_examples = True

    wtp = Wtp()
    wxr = WiktextractContext(wtp, config)
    wxr.wtp.start_page(word)
    return parse_page(wxr, word, WIKITEXT_SNIPPET)


def _fetch_rest_html(word: str) -> str:
    encoded = urllib.parse.quote(word)
    url = REST_ENDPOINT.format(title=encoded)
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "wiktextract-regression/1.0 (+https://github.com/tatuylonen/wiktextract)",
        },
    )
    with urllib.request.urlopen(request) as response:
        if response.status != 200:
            raise RuntimeError(
                f"REST fetch failed for {word!r} with status {response.status}"
            )
        return response.read().decode("utf-8")


def run_path_b(word: str, rest_html_override: Path | None) -> List[dict]:
    if rest_html_override is not None:
        html_text = rest_html_override.read_text(encoding="utf-8")
    elif word == "lay":
        html_text = HTML_FIXTURE.read_text(encoding="utf-8")
    else:
        html_text = _fetch_rest_html(word)
    return parse_mobile_html(word, html_text)


def write_jsonl(path: Path, items: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


def highlight_contains(items: Iterable[dict], needle: str) -> List[str]:
    matches: List[str] = []
    for record in items:
        for sense in record.get("senses", []):
            for example in sense.get("examples", []) or []:
                text = example.get("text") or ""
                if needle in text:
                    matches.append(
                        f"{record.get('word')} / {record.get('pos')}: "
                        f"{text}"
                    )
    return matches


def main() -> None:
    args = parse_args()
    out_a = Path(args.out_a)
    out_b = Path(args.out_b)
    rest_override = Path(args.rest_html) if args.rest_html else None

    data_a = run_path_a(args.word)
    data_b = run_path_b(args.word, rest_override)

    write_jsonl(out_a, data_a)
    write_jsonl(out_b, data_b)

    if args.contains:
        matches_a = highlight_contains(data_a, args.contains)
        matches_b = highlight_contains(data_b, args.contains)
        print("=== Path A matches ===")
        if matches_a:
            for line in matches_a:
                print(line)
        else:
            print("(none)")
        print("=== Path B matches ===")
        if matches_b:
            for line in matches_b:
                print(line)
        else:
            print("(none)")


if __name__ == "__main__":
    main()
