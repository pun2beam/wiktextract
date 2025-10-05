#!/usr/bin/env python3
"""Reproduce the lay example assignment issue via two extraction paths."""

from __future__ import annotations

import argparse
import json
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate JSONL outputs for the word 'lay' via two extraction "
            "paths: direct wikitext parsing (A) and REST-style HTML parsing "
            "(B)."
        )
    )
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
    return parser.parse_args()


def run_path_a() -> List[dict]:
    config = WiktionaryConfig()
    config.capture_language_codes = ["en"]
    config.capture_examples = True

    wtp = Wtp()
    wxr = WiktextractContext(wtp, config)
    wxr.wtp.start_page("lay")
    return parse_page(wxr, "lay", WIKITEXT_SNIPPET)


def run_path_b() -> List[dict]:
    html_text = HTML_FIXTURE.read_text(encoding="utf-8")
    return parse_mobile_html("lay", html_text)


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

    data_a = run_path_a()
    data_b = run_path_b()

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
