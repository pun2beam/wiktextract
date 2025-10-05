"""Utilities for parsing REST/Parsoid-rendered HTML for targeted debugging.

This module implements a deliberately small HTML extraction pipeline that is
tailored for regression testing around the English entry for "lay".  The
production extractor operates on wikitext, but REST endpoints return fully
rendered HTML where the surrounding structure (for example, heading
breadcrumbs) is easy to lose track of.  The helpers here allow us to build
synthetic fixtures that mimic that environment and observe how examples are
assigned across part-of-speech boundaries without letting them drift across
heading changes.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from typing import Iterable

from lxml import html

from mediawiki_langcodes import name_to_code


@dataclass
class _SenseContext:
    """Book-keeping information for a sense extracted from HTML."""

    headings: tuple[str, ...]
    sense: dict


def _build_heading_map(tree: html.HtmlElement) -> dict[html.HtmlElement, tuple[str, ...]]:
    """Create a mapping from every node to the latest heading breadcrumb."""

    heading_map: dict[html.HtmlElement, tuple[str, ...]] = {}
    current_h2: str | None = None
    current_h3: str | None = None
    current_h4: str | None = None

    for node in tree.iter():
        tag = node.tag.lower() if hasattr(node, "tag") else ""
        if tag == "h2":
            text = node.text_content().strip()
            if text:
                current_h2 = text
                current_h3 = None
                current_h4 = None
        elif tag == "h3":
            text = node.text_content().strip()
            if text:
                current_h3 = text
                current_h4 = None
        elif tag == "h4":
            text = node.text_content().strip()
            if text:
                current_h4 = text

        headings: list[str] = []
        if current_h2:
            headings.append(current_h2)
        if current_h3:
            headings.append(current_h3)
        if current_h4:
            headings.append(current_h4)
        heading_map[node] = tuple(headings)

    return heading_map


def _normalize_whitespace(text: str) -> str:
    return " ".join(text.split())


def _extract_gloss(li: html.HtmlElement) -> str:
    # Prefer the first paragraph; fall back to the list item text content.
    paragraph = li.xpath(".//p[1]")
    if paragraph:
        return _normalize_whitespace(paragraph[0].text_content())
    return _normalize_whitespace(li.text_content())


def _paths_match(sense_path: tuple[str, ...], example_path: tuple[str, ...]) -> bool:
    if not sense_path or not example_path:
        return False
    min_len = min(len(sense_path), len(example_path))
    return sense_path[:min_len] == example_path[:min_len]


def parse_mobile_html(title: str, html_text: str) -> list[dict]:
    """Parse minimal REST/Parsoid HTML into wiktextract-style JSON records.

    This helper focuses on the subset of HTML used in the regression fixtures
    (language/etymology/POS sections expressed with nested ``<section>`` tags,
    ordered lists for glosses, and ``div[data-type="example"]`` blocks for
    usage examples).  It is intentionally small in scope and is not meant to be
    a complete replacement for the wikitext-based extractor.

    The implementation records heading breadcrumbs for both senses and
    examples so that usage examples remain anchored to the correct
    part-of-speech even if other senses appear later in the document.
    """

    tree = html.fromstring(html_text)
    heading_map = _build_heading_map(tree)

    entries: "OrderedDict[tuple[str, str], dict]" = OrderedDict()
    sense_contexts: list[_SenseContext] = []

    sense_nodes = tree.xpath("//section[h4]/ol/li")
    for li in sense_nodes:
        headings = heading_map.get(li, ())
        if not headings:
            continue
        lang = headings[0]
        pos = headings[-1]
        lang_code = name_to_code(lang) or ""

        key = (lang, pos)
        if key not in entries:
            entries[key] = {
                "word": title,
                "lang": lang,
                "lang_code": lang_code,
                "pos": pos.lower(),
                "senses": [],
            }

        gloss_text = _extract_gloss(li)
        sense: dict[str, Iterable | str] = {}
        if gloss_text:
            sense["glosses"] = [gloss_text]
        entries[key]["senses"].append(sense)
        sense_contexts.append(_SenseContext(headings=headings, sense=sense))

    example_nodes = tree.xpath("//div[@data-type='example']")
    examples: list[tuple[tuple[str, ...], dict]] = []
    for node in example_nodes:
        headings = heading_map.get(node, ())
        text = _normalize_whitespace(node.text_content())
        if not text:
            continue
        examples.append((headings, {"text": text}))

    for headings, example in examples:
        target_sense = None
        for context in reversed(sense_contexts):
            if _paths_match(context.headings, headings):
                target_sense = context.sense
                break
        if target_sense is None and sense_contexts:
            # Fallback: preserve previous behaviour when no breadcrumb matches.
            target_sense = sense_contexts[-1].sense
        if target_sense is not None:
            target_sense.setdefault("examples", []).append(example)

    return list(entries.values())

