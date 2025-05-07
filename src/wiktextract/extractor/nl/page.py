import re
from typing import Any

from mediawiki_langcodes import name_to_code
from wikitextprocessor.parser import (
    LEVEL_KIND_FLAGS,
    LevelNode,
    NodeKind,
)

from ...page import clean_node
from ...wxr_context import WiktextractContext
from .descendant import extract_descendant_section
from .etymology import extract_etymology_section
from .inflection import FORMS_TABLE_TEMPLATES, extract_inflection_template
from .linkage import extract_fixed_preposition_section, extract_linkage_section
from .models import Etymology, Sense, WordEntry
from .pos import extract_pos_section
from .section_titles import LINKAGE_SECTIONS, POS_DATA
from .sound import extract_hyphenation_section, extract_sound_section
from .spelling_form import extract_spelling_form_section
from .translation import extract_translation_section


def extract_section_categories(
    wxr: WiktextractContext, word_entry: WordEntry, level_node: LevelNode
) -> None:
    for link_node in level_node.find_child(NodeKind.LINK):
        clean_node(wxr, word_entry, link_node)


def select_word_entry(
    page_data: list[WordEntry], base_data: WordEntry
) -> WordEntry:
    # use a function not a variable because new data could be appended to
    # `page_data` after the variable is created
    return (
        page_data[-1]
        if len(page_data) > 0 and page_data[-1].lang_code == base_data.lang_code
        else base_data
    )


def parse_section(
    wxr: WiktextractContext,
    page_data: list[WordEntry],
    base_data: WordEntry,
    forms_data: WordEntry,
    level_node: LevelNode,
) -> list[Etymology]:
    # title templates
    # https://nl.wiktionary.org/wiki/Categorie:Lemmasjablonen
    title_text = clean_node(wxr, None, level_node.largs)
    title_text = re.sub(r"\s+#?\d+:?$", "", title_text)
    wxr.wtp.start_subsection(title_text)
    etymology_data = []

    if title_text in POS_DATA:
        last_data_len = len(page_data)
        extract_pos_section(
            wxr, page_data, base_data, forms_data, level_node, title_text
        )
        if len(page_data) == last_data_len and title_text in LINKAGE_SECTIONS:
            extract_linkage_section(
                wxr,
                page_data[-1] if len(page_data) > 0 else base_data,
                level_node,
                LINKAGE_SECTIONS[title_text],
            )
    elif title_text == "Uitspraak":
        extract_sound_section(
            wxr, select_word_entry(page_data, base_data), level_node
        )
    elif title_text in LINKAGE_SECTIONS:
        extract_linkage_section(
            wxr,
            select_word_entry(page_data, base_data),
            level_node,
            LINKAGE_SECTIONS[title_text],
        )
    elif title_text == "Vertalingen":
        extract_translation_section(
            wxr, select_word_entry(page_data, base_data), level_node
        )
    elif title_text == "Woordafbreking":
        extract_hyphenation_section(
            wxr, select_word_entry(page_data, base_data), level_node
        )
    elif title_text == "Woordherkomst en -opbouw":
        etymology_data = extract_etymology_section(wxr, level_node)
    elif title_text in ["Schrijfwijzen", "Verdere woordvormen"]:
        extract_spelling_form_section(
            wxr, select_word_entry(page_data, base_data), level_node
        )
    elif title_text == "Opmerkingen":
        extract_note_section(
            wxr, select_word_entry(page_data, base_data), level_node
        )
    elif title_text == "Overerving en ontlening":
        extract_descendant_section(
            wxr, select_word_entry(page_data, base_data), level_node
        )
    elif title_text == "Vaste voorzetsels":
        extract_fixed_preposition_section(
            wxr, select_word_entry(page_data, base_data), level_node
        )
    elif title_text in [
        "Gangbaarheid",
        "Meer informatie",
        "Verwijzingen",
        "Citaten",
    ]:
        pass  # ignore
    elif not title_text.startswith(("Vervoeging", "Verbuiging")):
        wxr.wtp.debug(f"unknown title: {title_text}", sortid="nl/page/60")

    for next_level in level_node.find_child(LEVEL_KIND_FLAGS):
        parse_section(wxr, page_data, base_data, forms_data, next_level)
    extract_section_categories(
        wxr, select_word_entry(page_data, base_data), level_node
    )
    is_first_forms_template = True
    for t_node in level_node.find_child(NodeKind.TEMPLATE):
        if t_node.template_name in FORMS_TABLE_TEMPLATES:
            if is_first_forms_template:
                is_first_forms_template = False
                if len(forms_data.forms) > 0:
                    forms_data.forms.clear()
                    forms_data.extracted_vervoeging_page = False
            extract_inflection_template(
                wxr,
                page_data[-1]
                if title_text.startswith(("Vervoeging", "Verbuiging"))
                and len(page_data) > 0
                and page_data[-1].lang_code == base_data.lang_code
                else forms_data,
                t_node,
            )
    return etymology_data


def parse_page(
    wxr: WiktextractContext, page_title: str, page_text: str
) -> list[dict[str, Any]]:
    # page layout
    # https://nl.wiktionary.org/wiki/WikiWoordenboek:Stramien
    # language templates
    # https://nl.wiktionary.org/wiki/Categorie:Hoofdtaalsjablonen
    if page_title.endswith("/vervoeging"):
        return []  # skip conjugation pages
    wxr.wtp.start_page(page_title)
    tree = wxr.wtp.parse(page_text, pre_expand=True)
    page_data: list[WordEntry] = []
    for level2_node in tree.find_child(NodeKind.LEVEL2):
        lang_name = clean_node(wxr, None, level2_node.largs)
        lang_code = name_to_code(lang_name, "nl")
        if lang_code == "":
            lang_code = "unknown"
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
        )
        forms_data = base_data.model_copy(deep=True)
        extract_section_categories(wxr, base_data, level2_node)
        etymology_data = []
        for t_node in level2_node.find_child(NodeKind.TEMPLATE):
            extract_inflection_template(wxr, forms_data, t_node)
        for next_level_node in level2_node.find_child(LEVEL_KIND_FLAGS):
            new_e_data = parse_section(
                wxr, page_data, base_data, forms_data, next_level_node
            )
            if len(new_e_data) > 0:
                etymology_data = new_e_data
        for data in page_data:
            if data.lang_code == lang_code:
                for e_data in etymology_data:
                    if (
                        e_data.index == data.etymology_index
                        or e_data.index == ""
                    ):
                        data.etymology_texts.append(e_data.text)
                        data.categories.extend(e_data.categories)

    for data in page_data:
        for sense in data.senses:
            if len(sense.glosses) == 0:
                sense.tags.append("no-gloss")
        if len(data.senses) == 0:
            data.senses.append(Sense(tags=["no-gloss"]))
    return [m.model_dump(exclude_defaults=True) for m in page_data]


def extract_note_section(
    wxr: WiktextractContext, word_entry: WordEntry, level_node: LevelNode
) -> None:
    for list_item in level_node.find_child_recursively(NodeKind.LIST_ITEM):
        note_str = clean_node(wxr, word_entry, list_item.children)
        if len(note_str) > 0:
            word_entry.notes.append(note_str)
