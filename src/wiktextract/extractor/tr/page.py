import string
from typing import Any

from mediawiki_langcodes import name_to_code
from wikitextprocessor.parser import LEVEL_KIND_FLAGS, LevelNode, NodeKind

from ...page import clean_node
from ...wxr_context import WiktextractContext
from .etymology import extract_etymology_section
from .inflection import extract_inflection_section
from .linkage import extract_linkage_section
from .models import Sense, WordEntry
from .pos import extract_note_section, extract_pos_section
from .section_titles import LINKAGE_SECTIONS, LINKAGE_TAGS, POS_DATA
from .sound import extract_sound_section
from .translation import extract_translation_section


def parse_section(
    wxr: WiktextractContext,
    page_data: list[WordEntry],
    base_data: WordEntry,
    level_node: LevelNode,
) -> None:
    title_text = clean_node(wxr, None, level_node.largs)
    wxr.wtp.start_subsection(title_text)
    title_text = title_text.rstrip(string.digits + string.whitespace)
    if title_text in POS_DATA:
        extract_pos_section(wxr, page_data, base_data, level_node, title_text)
        if len(page_data[-1].senses) == 0 and title_text in LINKAGE_SECTIONS:
            page_data.pop()
            extract_linkage_section(
                wxr,
                page_data[-1] if len(page_data) > 0 else base_data,
                level_node,
                LINKAGE_SECTIONS[title_text],
                LINKAGE_TAGS.get(title_text, []),
            )
    elif title_text == "Köken":
        if level_node.contain_node(LEVEL_KIND_FLAGS):
            base_data = base_data.model_copy(deep=True)
        extract_etymology_section(wxr, base_data, level_node)
    elif title_text == "Söyleniş":
        if level_node.contain_node(LEVEL_KIND_FLAGS):
            base_data = base_data.model_copy(deep=True)
        extract_sound_section(wxr, base_data, level_node)
    elif title_text == "Çeviriler":
        extract_translation_section(
            wxr, page_data[-1] if len(page_data) > 0 else base_data, level_node
        )
    elif title_text in LINKAGE_SECTIONS:
        extract_linkage_section(
            wxr,
            page_data[-1] if len(page_data) > 0 else base_data,
            level_node,
            LINKAGE_SECTIONS[title_text],
            LINKAGE_TAGS.get(title_text, []),
        )
    elif title_text == "Açıklamalar":
        extract_note_section(
            wxr, page_data[-1] if len(page_data) > 0 else base_data, level_node
        )
    elif title_text == "Çekimleme":
        extract_inflection_section(
            wxr, page_data[-1] if len(page_data) > 0 else base_data, level_node
        )
    elif title_text not in ["Kaynakça", "Ek okumalar"]:
        wxr.wtp.debug(
            f"Unknown section: {title_text}",
            sortid="extractor/tr/page/parse_section/70",
        )

    for next_level in level_node.find_child(LEVEL_KIND_FLAGS):
        parse_section(wxr, page_data, base_data, next_level)

    for link_node in level_node.find_child(NodeKind.LINK):
        clean_node(
            wxr, page_data[-1] if len(page_data) > 0 else base_data, link_node
        )


def parse_page(
    wxr: WiktextractContext, page_title: str, page_text: str
) -> list[dict[str, Any]]:
    # page layout
    # https://tr.wiktionary.org/wiki/Vikisözlük:Girdilerin_biçimi
    wxr.wtp.start_page(page_title)
    tree = wxr.wtp.parse(page_text, pre_expand=True)
    page_data: list[WordEntry] = []
    for level2_node in tree.find_child(NodeKind.LEVEL2):
        lang_name = clean_node(wxr, None, level2_node.largs)
        lang_code = name_to_code(lang_name, "id") or "unknown"
        wxr.wtp.start_section(lang_name)
        base_data = WordEntry(
            word=wxr.wtp.title,
            lang_code=lang_code,
            lang=lang_name,
            pos="unknown",
        )
        for next_level_node in level2_node.find_child(LEVEL_KIND_FLAGS):
            parse_section(wxr, page_data, base_data, next_level_node)

    for data in page_data:
        if len(data.senses) == 0:
            data.senses.append(Sense(tags=["no-gloss"]))
    return [m.model_dump(exclude_defaults=True) for m in page_data]
