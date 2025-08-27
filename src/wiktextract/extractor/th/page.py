import string
from typing import Any

from mediawiki_langcodes import name_to_code
from wikitextprocessor.parser import LEVEL_KIND_FLAGS, LevelNode, NodeKind

from ...page import clean_node
from ...wxr_context import WiktextractContext
from .alt_form import extract_alt_form_section, extract_romanization_section
from .descendant import extract_descendant_section
from .etymology import extract_etymology_section
from .linkage import extract_linkage_section
from .models import Sense, WordEntry
from .pos import (
    extract_note_section,
    extract_pos_section,
    extract_usage_note_section,
)
from .section_titles import LINKAGE_SECTIONS, POS_DATA, TRANSLATION_SECTIONS
from .sound import extract_sound_section
from .translation import extract_translation_section


def parse_section(
    wxr: WiktextractContext,
    page_data: list[WordEntry],
    base_data: WordEntry,
    level_node: LevelNode,
) -> None:
    title_text = clean_node(wxr, None, level_node.largs)
    title_text = title_text.rstrip(string.digits + string.whitespace)
    wxr.wtp.start_subsection(title_text)
    if title_text in POS_DATA:
        extract_pos_section(wxr, page_data, base_data, level_node, title_text)
        if len(page_data[-1].senses) == 0 and title_text in LINKAGE_SECTIONS:
            page_data.pop()
            extract_linkage_section(
                wxr,
                page_data[-1] if len(page_data) > 0 else base_data,
                level_node,
                LINKAGE_SECTIONS[title_text],
            )
        elif (
            len(page_data[-1].senses) == 0 and title_text == "การถอดเป็นอักษรโรมัน"
        ):
            page_data.pop()
            extract_romanization_section(
                wxr,
                page_data[-1] if len(page_data) > 0 else base_data,
                level_node,
            )
    elif title_text == "รากศัพท์":
        if level_node.contain_node(LEVEL_KIND_FLAGS):
            base_data = base_data.model_copy(deep=True)
        extract_etymology_section(wxr, base_data, level_node)
    elif title_text in TRANSLATION_SECTIONS:
        extract_translation_section(
            wxr, page_data[-1] if len(page_data) > 0 else base_data, level_node
        )
    elif title_text in LINKAGE_SECTIONS:
        extract_linkage_section(
            wxr,
            page_data[-1] if len(page_data) > 0 else base_data,
            level_node,
            LINKAGE_SECTIONS[title_text],
        )
    elif title_text == "คำสืบทอด":
        extract_descendant_section(
            wxr, page_data[-1] if len(page_data) > 0 else base_data, level_node
        )
    elif title_text.startswith(("การออกเสียง", "การอ่านออกเสียง", "ออกเสียง")):
        extract_sound_section(wxr, base_data, level_node)
    elif title_text == "รูปแบบอื่น":
        extract_alt_form_section(
            wxr,
            page_data[-1]
            if len(page_data) > 0
            and page_data[-1].lang_code == base_data.lang_code
            and page_data[-1].pos == base_data.pos
            else base_data,
            level_node,
        )
    elif title_text == "การใช้":
        extract_note_section(
            wxr, page_data[-1] if len(page_data) > 0 else base_data, level_node
        )
    elif title_text == "หมายเหตุการใช้":
        extract_usage_note_section(
            wxr, page_data[-1] if len(page_data) > 0 else base_data, level_node
        )
    elif title_text not in [
        "ดูเพิ่ม",  # see more
        "อ้างอิง",  # references
        "อ่านเพิ่ม",  # read more
        "อ่านเพิ่มเติม",  # read more
        "รากอักขระ",  # glyph origin
        "การผันรูป",  # conjugation
        "การผัน",  # conjugation
        "คำกริยาในรูปต่าง ๆ",  # verb forms
        "การอ่าน",  # Japanese readings
        "การผันคำกริยา",  # conjugation
        "การผันคำ",  # inflection
        "การกลายรูป",  # conjugation
        "การผันคำนาม",  # inflection
    ]:
        wxr.wtp.debug(f"Unknown title: {title_text}")

    for next_level in level_node.find_child(LEVEL_KIND_FLAGS):
        parse_section(wxr, page_data, base_data, next_level)


def parse_page(
    wxr: WiktextractContext, page_title: str, page_text: str
) -> list[dict[str, Any]]:
    # page layout
    # https://th.wiktionary.org/wiki/วิธีใช้:คู่มือในการเขียน

    # skip translation pages
    if page_title.endswith("/คำแปลภาษาอื่น"):
        return []
    wxr.wtp.start_page(page_title)
    tree = wxr.wtp.parse(page_text, pre_expand=True)
    page_data: list[WordEntry] = []
    for level2_node in tree.find_child(NodeKind.LEVEL2):
        lang_name = clean_node(wxr, None, level2_node.largs)
        lang_name = lang_name.removeprefix("ภาษา")
        lang_code = name_to_code(lang_name, "th")
        if lang_code == "":
            lang_code = "unknown"
        if lang_name == "":
            lang_name = "unknown"
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
