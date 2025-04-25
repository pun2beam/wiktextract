from wikitextprocessor.parser import (
    LEVEL_KIND_FLAGS,
    NodeKind,
    TemplateNode,
    WikiNode,
    WikiNodeChildrenList,
)

from ...page import clean_node
from ...wxr_context import WiktextractContext
from ...wxr_logging import logger
from .conjugation import extract_conjugation_section
from .etymology import process_etymology_block
from .example import extract_example
from .gloss import extract_gloss, process_ambito_template, process_uso_template
from .inflection import extract_inflection
from .linkage import (
    extract_alt_form_section,
    extract_linkage_section,
    process_linkage_template,
)
from .models import Sense, WordEntry
from .pronunciation import process_pron_graf_template
from .section_titles import (
    IGNORED_TITLES,
    LINKAGE_TITLES,
    POS_TITLES,
    TRANSLATIONS_TITLES,
)
from .sense_data import process_sense_data_list
from .translation import extract_translation_section


def parse_entries(
    wxr: WiktextractContext,
    page_data: list[WordEntry],
    base_data: WordEntry,
    level_node: WikiNode,
):
    """
    Parse entries in a language section (level 2) or etymology section (level 3)
    and extract data affecting all subsections, e.g. the {pron-graf} template.

    A language section may contain multiple entries, usually devided by
    different POS with level 3 headings,
    e.g. https://es.wiktionary.org/wiki/agua or
    https://es.wiktionary.org/wiki/love

    If a word has distinct etmylogies, these are separated by level 3 headings
    and subdivided by their POS at level 4 headings,
    e.g. https://es.wiktionary.org/wiki/churro
    """

    # This might not be necessary but it's to prevent that base_data is applied
    # to entries that it shouldn't be applied to
    base_data_copy = base_data.model_copy(deep=True)
    unexpected_nodes = []
    # Parse data affecting all subsections and add to base_data_copy
    for node in level_node.invert_find_child(LEVEL_KIND_FLAGS):
        if (
            isinstance(node, TemplateNode)
            and node.template_name == "pron-graf"
            and wxr.config.capture_pronunciation
        ):
            process_pron_graf_template(wxr, base_data_copy, node)
        elif (
            isinstance(node, WikiNode)
            and node.kind == NodeKind.LIST
            and node.sarg == ":*"
        ):
            # XXX: There might be other uses for this kind of list which are
            # being ignored here
            continue
        elif isinstance(node, WikiNode) and node.kind == NodeKind.LINK:
            clean_node(wxr, base_data_copy, node)
        else:
            unexpected_nodes.append(node)

    if unexpected_nodes:
        wxr.wtp.debug(
            f"Found unexpected nodes {unexpected_nodes} "
            f"in section {level_node.largs}",
            sortid="extractor/es/page/parse_entries/69",
        )

    for sub_level_node in level_node.find_child(LEVEL_KIND_FLAGS):
        parse_section(wxr, page_data, base_data_copy, sub_level_node)


def parse_section(
    wxr: WiktextractContext,
    page_data: list[WordEntry],
    base_data: WordEntry,
    level_node: WikiNode,
) -> None:
    """
    Parses indidividual sibling sections of an entry,
    e.g. https://es.wiktionary.org/wiki/amor:

    === Etimología ===
    === {{sustantivo masculino|es}} ===
    === Locuciones ===
    """

    categories = {}
    section_title = clean_node(wxr, categories, level_node.largs)
    original_section_title = section_title
    section_title = section_title.lower()
    wxr.wtp.start_subsection(original_section_title)

    pos_template_name = ""
    for level_node_template in level_node.find_content(NodeKind.TEMPLATE):
        pos_template_name = level_node_template.template_name

    if section_title in IGNORED_TITLES:
        pass
    elif pos_template_name in POS_TITLES or section_title in POS_TITLES:
        pos_data = POS_TITLES.get(
            pos_template_name, POS_TITLES.get(section_title)
        )
        pos_type = pos_data["pos"]
        page_data.append(base_data.model_copy(deep=True))
        page_data[-1].pos = pos_type
        page_data[-1].pos_title = original_section_title
        page_data[-1].tags.extend(pos_data.get("tags", []))
        page_data[-1].categories.extend(categories.get("categories", []))
        process_pos_block(wxr, page_data, level_node)
        if len(page_data[-1].senses) == 0 and "form-of" in page_data[-1].tags:
            page_data.pop()
    elif (
        section_title.startswith("etimología")
        and wxr.config.capture_etymologies
    ):
        process_etymology_block(wxr, base_data, level_node)
    elif (
        section_title in TRANSLATIONS_TITLES and wxr.config.capture_translations
    ):
        if len(page_data) == 0:
            page_data.append(base_data.model_copy(deep=True))
        extract_translation_section(wxr, page_data, level_node)
    elif section_title in LINKAGE_TITLES:
        if len(page_data) == 0:
            page_data.append(base_data.model_copy(deep=True))
        extract_linkage_section(
            wxr, page_data, level_node, LINKAGE_TITLES[section_title]
        )
    elif section_title == "conjugación":
        if len(page_data) == 0:
            page_data.append(base_data.model_copy(deep=True))
        extract_conjugation_section(wxr, page_data, level_node)
    elif section_title == "formas alternativas":
        extract_alt_form_section(
            wxr, page_data[-1] if len(page_data) > 0 else base_data, level_node
        )
    else:
        wxr.wtp.debug(
            f"Unprocessed section: {section_title}",
            sortid="extractor/es/page/parse_section/48",
        )

    for next_level_node in level_node.find_child(LEVEL_KIND_FLAGS):
        parse_section(wxr, page_data, base_data, next_level_node)


def process_pos_block(
    wxr: WiktextractContext,
    page_data: list[WordEntry],
    pos_level_node: WikiNode,
):
    """
    Senses are indicated by ListNodes with a semicolon as argument. They can be
    followed by multiple nodes that add different kinds of information to the
    sense. These nodes are collected in sense_children and processed after the
    next sense is encountered or after the last sense has been processed.
    """

    child_nodes = list(pos_level_node.filter_empty_str_child())
    # All non-gloss nodes that add additional information to a sense
    sense_children: WikiNodeChildrenList = []

    for child in child_nodes:
        if (
            isinstance(child, WikiNode)
            and child.kind == NodeKind.LIST
            and child.sarg == ";"
        ):
            # Consume sense_children of previous sense and extract gloss of
            # new sense
            process_sense_children(wxr, page_data, sense_children)
            sense_children = []

            extract_gloss(wxr, page_data, child)

        elif page_data[-1].senses:
            sense_children.append(child)

        else:
            # Process nodes before first sense
            if isinstance(child, TemplateNode) and (
                "inflect" in child.template_name
                or "v.conj" in child.template_name
            ):
                extract_inflection(wxr, page_data, child)
            elif (
                isinstance(child, WikiNode)
                and child.kind == NodeKind.LINK
                and "Categoría" in child.largs[0][0]
            ):
                clean_node(wxr, page_data[-1], child)
            else:
                wxr.wtp.debug(
                    f"Found unexpected node in pos_block: {child}",
                    sortid="extractor/es/page/process_pos_block/184",
                )

    if pos_level_node.contain_node(NodeKind.LIST):
        process_sense_children(wxr, page_data, sense_children)
    else:
        sense = Sense()
        gloss_text = clean_node(
            wxr, sense, list(pos_level_node.invert_find_child(LEVEL_KIND_FLAGS))
        )
        if len(gloss_text) > 0:
            sense.glosses.append(gloss_text)
            page_data[-1].senses.append(sense)


def process_sense_children(
    wxr: WiktextractContext,
    page_data: list[WordEntry],
    sense_children: WikiNodeChildrenList,
) -> None:
    """
    In most cases additional information to a sense is given via special
    templates or lists. However, sometimes string nodes are used to add
    information to a preceeding template or list.

    This function collects the nodes that form a group and calls the relevant
    methods for extraction.
    """

    def starts_new_group(child: WikiNode) -> bool:
        # Nested function for readibility
        return isinstance(child, WikiNode) and (
            child.kind == NodeKind.TEMPLATE
            or child.kind == NodeKind.LIST
            or child.kind == NodeKind.LINK
        )

    def process_group(
        wxr: WiktextractContext,
        page_data: list[WordEntry],
        group: WikiNodeChildrenList,
    ) -> None:
        # Nested function for readibility
        if len(group) == 0:
            return
        elif isinstance(group[0], TemplateNode):
            template_name = group[0].template_name
            if template_name == "clear":
                return
            elif template_name.removesuffix("s") in LINKAGE_TITLES:
                process_linkage_template(wxr, page_data[-1], group[0])
            elif template_name == "ejemplo":
                extract_example(wxr, page_data[-1].senses[-1], group)
            elif template_name == "uso":
                process_uso_template(wxr, page_data[-1].senses[-1], group[0])
            elif template_name == "ámbito":
                process_ambito_template(wxr, page_data[-1].senses[-1], group[0])
            else:
                wxr.wtp.debug(
                    f"Found unexpected group specifying a sense: {group},"
                    f"head template {template_name}",
                    sortid="extractor/es/page/process_group/102",
                )

        elif isinstance(group[0], WikiNode) and group[0].kind == NodeKind.LIST:
            list_node = group[0]
            # List groups seem to not be followed by string nodes.
            # We, therefore, only process the list_node.
            process_sense_data_list(wxr, page_data[-1], list_node)

        elif (
            isinstance(child, WikiNode)
            and child.kind == NodeKind.LINK
            and "Categoría" in child.largs[0][0]
        ):
            # Extract sense categories
            clean_node(wxr, page_data[-1].senses[-1], child)

        else:
            wxr.wtp.debug(
                f"Found unexpected group specifying a sense: {group}",
                sortid="extractor/es/page/process_group/117",
            )

    group: WikiNodeChildrenList = []
    for child in sense_children:
        if starts_new_group(child):
            process_group(wxr, page_data, group)
            group = []
        group.append(child)
    process_group(wxr, page_data, group)


def parse_page(
    wxr: WiktextractContext, page_title: str, page_text: str
) -> list[dict[str, any]]:
    # style guide
    # https://es.wiktionary.org/wiki/Wikcionario:Guía_de_estilo
    # entry layout
    # https://es.wiktionary.org/wiki/Wikcionario:Estructura
    if wxr.config.verbose:
        logger.info(f"Parsing page: {page_title}")

    wxr.wtp.start_page(page_title)
    tree = wxr.wtp.parse(page_text)
    page_data: list[WordEntry] = []
    for level2_node in tree.find_child(NodeKind.LEVEL2):
        categories = {}
        lang_code = "unknown"
        lang_name = "unknown"
        section_title = clean_node(wxr, None, level2_node.largs)
        if section_title.lower() == "referencias y notas":
            continue
        for subtitle_template in level2_node.find_content(NodeKind.TEMPLATE):
            # https://es.wiktionary.org/wiki/Plantilla:lengua
            # https://es.wiktionary.org/wiki/Apéndice:Códigos_de_idioma
            if subtitle_template.template_name == "lengua":
                lang_code = subtitle_template.template_parameters.get(1).lower()
                lang_name = clean_node(wxr, categories, subtitle_template)
                break
        if (
            wxr.config.capture_language_codes is not None
            and lang_code not in wxr.config.capture_language_codes
        ):
            continue
        wxr.wtp.start_section(lang_name)
        base_data = WordEntry(
            lang=lang_name,
            lang_code=lang_code,
            word=page_title,
            pos="unknown",
            categories=categories.get("categories", []),
        )
        parse_entries(wxr, page_data, base_data, level2_node)

    for data in page_data:
        if len(data.senses) == 0:
            data.senses.append(Sense(tags=["no-gloss"]))
    return [d.model_dump(exclude_defaults=True) for d in page_data]
