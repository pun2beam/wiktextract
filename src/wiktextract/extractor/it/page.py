from typing import Any

from wikitextprocessor.parser import LEVEL_KIND_FLAGS, LevelNode, NodeKind

from ...page import clean_node
from ...wxr_context import WiktextractContext
from .etymology import extract_citation_section, extract_etymology_section
from .linkage import extract_linkage_section
from .models import Sense, WordEntry
from .pos import extract_note_section, extract_pos_section
from .section_titles import LINKAGE_SECTIONS, POS_DATA
from .sound import extract_hyphenation_section, extract_pronunciation_section
from .translation import extract_translation_section


def parse_section(
    wxr: WiktextractContext,
    page_data: list[WordEntry],
    base_data: WordEntry,
    level_node: LevelNode,
) -> None:
    title_text = clean_node(wxr, None, level_node.largs)
    if title_text in POS_DATA:
        wxr.wtp.start_subsection(title_text)
        extract_pos_section(wxr, page_data, base_data, level_node, title_text)
    elif title_text == "Traduzione":
        wxr.wtp.start_subsection(title_text)
        extract_translation_section(wxr, page_data, level_node)
    elif title_text == "Etimologia / Derivazione":
        wxr.wtp.start_subsection(title_text)
        extract_etymology_section(wxr, page_data, level_node)
    elif title_text == "Citazione":
        wxr.wtp.start_subsection(title_text)
        extract_citation_section(wxr, page_data, level_node)
    elif title_text == "Sillabazione":
        wxr.wtp.start_subsection(title_text)
        extract_hyphenation_section(wxr, page_data, level_node)
    elif title_text == "Pronuncia":
        wxr.wtp.start_subsection(title_text)
        extract_pronunciation_section(wxr, page_data, level_node)
    elif title_text in LINKAGE_SECTIONS:
        wxr.wtp.start_subsection(title_text)
        extract_linkage_section(
            wxr, page_data, level_node, LINKAGE_SECTIONS[title_text]
        )
    elif title_text == "Uso / Precisazioni":
        extract_note_section(wxr, page_data, level_node)
    elif title_text not in ["Note / Riferimenti"]:
        wxr.wtp.debug(
            f"Unknown section: {title_text}",
            sortid="extractor/it/page/parse_section/49",
        )

    for next_level in level_node.find_child(LEVEL_KIND_FLAGS):
        parse_section(wxr, page_data, base_data, next_level)


def parse_page(
    wxr: WiktextractContext, page_title: str, page_text: str
) -> list[dict[str, Any]]:
    # page layout
    # https://it.wiktionary.org/wiki/Wikizionario:Manuale_di_stile
    # https://it.wiktionary.org/wiki/Aiuto:Come_iniziare_una_pagina
    wxr.wtp.start_page(page_title)
    tree = wxr.wtp.parse(page_text, pre_expand=True)
    page_data: list[WordEntry] = []
    for level2_node in tree.find_child(NodeKind.LEVEL2):
        lang_cats = {}
        lang_name = clean_node(wxr, lang_cats, level2_node.largs)
        if lang_name in ["Altri progetti", "Note / Riferimenti"]:
            continue
        lang_code = "unknown"
        for lang_template in level2_node.find_content(NodeKind.TEMPLATE):
            lang_code = lang_template.template_name.strip("-")
            break
        if (
            wxr.config.capture_language_codes is not None
            and lang_code not in wxr.config.capture_language_codes
        ):
            continue
        wxr.wtp.start_section(lang_name)
        base_data = WordEntry(
            word=wxr.wtp.title,
            lang_code=lang_code,
            lang=lang_name,
            pos="unknown",
            categories=lang_cats.get("categories", []),
        )
        for next_level_node in level2_node.find_child(LEVEL_KIND_FLAGS):
            parse_section(wxr, page_data, base_data, next_level_node)

    for data in page_data:
        if len(data.senses) == 0:
            data.senses.append(Sense(tags=["no-gloss"]))
    return [m.model_dump(exclude_defaults=True) for m in page_data]
