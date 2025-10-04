#!/usr/bin/env python3
"""Fetch a single Wiktionary page from the live site and extract it."""

from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from wikitextprocessor import Wtp

from wiktextract.config import WiktionaryConfig
from wiktextract.template_override import template_override_fns
from wiktextract.wiktionary import check_json_data, parse_page, write_json_data
from wiktextract.wxr_context import WiktextractContext

DEFAULT_USER_AGENT = (
    "wiktextract-debug/1.0 (+https://github.com/tatuylonen/wiktextract)"
)
EXPORT_XML_NAMESPACE = "{http://www.mediawiki.org/xml/export-0.11/}"


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Download a Wiktionary page via Special:Export and run the "
            "wiktextract parser on it."
        )
    )
    parser.add_argument("title", help="Title of the Wiktionary page to extract")
    parser.add_argument(
        "--edition",
        default="en",
        help=(
            "Language edition to use (default: en, resulting in "
            "https://<edition>.wiktionary.org)."
        ),
    )
    parser.add_argument(
        "--language-code",
        action="append",
        default=[],
        help=(
            "Language code(s) to capture. May be given multiple times. "
            "Defaults to the dump language and Translingual."
        ),
    )
    parser.add_argument(
        "--all-languages",
        action="store_true",
        help="Extract senses for all languages without filtering.",
    )
    parser.add_argument(
        "--out",
        default="-",
        help="Path to the output JSONL file (default: stdout).",
    )
    parser.add_argument(
        "--human-readable",
        action="store_true",
        help="Pretty-print JSON output instead of compact JSON lines.",
    )
    parser.add_argument(
        "--db-path",
        default=None,
        help=(
            "Optional SQLite database file to use for caching fetched pages. "
            "Defaults to a temporary file created by wikitextprocessor."
        ),
    )
    parser.add_argument(
        "--user-agent",
        default=DEFAULT_USER_AGENT,
        help="User-Agent header to send with HTTP requests.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Timeout in seconds for HTTP requests (default: 30).",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Reduce logging noise from wikitextprocessor.",
    )
    parser.add_argument(
        "--no-templates",
        action="store_true",
        help="Skip requesting templates via Special:Export (not recommended).",
    )
    parser.add_argument(
        "--print-debug",
        action="store_true",
        help="Print collected debug log messages to stderr after extraction.",
    )
    return parser.parse_args()


def build_capture_languages(
    edition: str, specified: Iterable[str], all_languages: bool
) -> Iterable[str] | None:
    if all_languages:
        return None
    capture = set(specified)
    if not capture:
        capture.update({edition, "mul"})
    return capture


def fetch_export_xml(
    edition: str,
    title: str,
    include_templates: bool,
    user_agent: str,
    timeout: float,
) -> str:
    params = {"pages": title, "curonly": "1"}
    if include_templates:
        params["templates"] = "1"
    query = urlencode(params)
    url = f"https://{edition}.wiktionary.org/wiki/Special:Export?{query}"
    request = Request(url, headers={"User-Agent": user_agent})
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.read().decode("utf-8")
    except HTTPError as exc:  # pragma: no cover - network error handling
        raise RuntimeError(
            f"HTTP error {exc.code} when fetching Special:Export: {exc.reason}"
        ) from exc
    except URLError as exc:  # pragma: no cover - network error handling
        raise RuntimeError(
            f"Failed to fetch Special:Export for {title!r}: {exc.reason}"
        ) from exc


def import_pages_into_wtp(
    wxr: WiktextractContext, xml_text: str, target_title: str
) -> tuple[str, str]:
    root = ET.fromstring(xml_text)
    page_nodes = root.findall(f"{EXPORT_XML_NAMESPACE}page")
    if not page_nodes:
        raise RuntimeError("Special:Export response did not contain any pages")

    primary_title = None
    primary_text = None
    for page in page_nodes:
        title_node = page.find(f"{EXPORT_XML_NAMESPACE}title")
        ns_node = page.find(f"{EXPORT_XML_NAMESPACE}ns")
        revision_node = page.find(f"{EXPORT_XML_NAMESPACE}revision")
        redirect_node = page.find(f"{EXPORT_XML_NAMESPACE}redirect")

        if title_node is None or ns_node is None:
            continue
        title = title_node.text or ""
        ns_text = ns_node.text or "0"
        try:
            namespace_id = int(ns_text)
        except ValueError:
            namespace_id = 0

        text = ""
        if revision_node is not None:
            text_node = revision_node.find(f"{EXPORT_XML_NAMESPACE}text")
            if text_node is not None and text_node.text is not None:
                text = text_node.text

        redirect_to = (
            redirect_node.get("title") if redirect_node is not None else None
        )
        wxr.wtp.add_page(title, namespace_id, text, redirect_to=redirect_to)

        is_main_namespace = namespace_id == 0
        if is_main_namespace and primary_title is None:
            primary_title = title
            primary_text = text
        if is_main_namespace and title.lower() == target_title.lower():
            primary_title = title
            primary_text = text

    wxr.wtp.db_conn.commit()

    if primary_title is None or primary_text is None:
        raise RuntimeError(
            "Unable to locate main namespace page in Special:Export response"
        )

    return primary_title, primary_text


def main() -> None:
    args = parse_arguments()

    capture_languages = build_capture_languages(
        args.edition, args.language_code, args.all_languages
    )

    config = WiktionaryConfig(
        dump_file_lang_code=args.edition,
        capture_language_codes=capture_languages,
    )

    wtp = Wtp(
        db_path=args.db_path,
        lang_code=args.edition,
        template_override_funcs=(
            template_override_fns if args.edition == "en" else {}
        ),
        extension_tags=config.allowed_html_tags,
        parser_function_aliases=config.parser_function_aliases,
        quiet=args.quiet,
    )

    wxr = WiktextractContext(wtp, config)

    xml_text = fetch_export_xml(
        args.edition,
        args.title,
        include_templates=not args.no_templates,
        user_agent=args.user_agent,
        timeout=args.timeout,
    )

    page_title, page_text = import_pages_into_wtp(wxr, xml_text, args.title)

    wxr.wtp.start_page(page_title)
    entries = parse_page(wxr, page_title, page_text)

    out_stream = sys.stdout if args.out == "-" else open(
        args.out, "w", encoding="utf-8"
    )
    try:
        for entry in entries:
            check_json_data(wxr, entry)
            write_json_data(entry, out_stream, args.human_readable)
    finally:
        if out_stream is not sys.stdout:
            out_stream.close()

    wxr.config.merge_return(wxr.wtp.to_return())

    if args.print_debug:
        for debug in wxr.config.debugs:
            sortid = debug.get("sortid", "")
            msg = debug.get("msg", "")
            if sortid:
                sys.stderr.write(f"[DEBUG:{sortid}] {msg}\n")
            else:
                sys.stderr.write(f"[DEBUG] {msg}\n")


if __name__ == "__main__":
    main()
