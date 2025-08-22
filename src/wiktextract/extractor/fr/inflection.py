import re
from dataclasses import dataclass

from wikitextprocessor.parser import NodeKind, TemplateNode, WikiNode

from ...page import clean_node
from ...wxr_context import WiktextractContext
from .models import Form, WordEntry
from .pronunciation import is_ipa_text
from .tags import translate_raw_tags


def extract_inflection(
    wxr: WiktextractContext, page_data: list[WordEntry], t_node: TemplateNode
):
    # inflection templates
    # https://fr.wiktionary.org/wiki/Catégorie:Modèles_d’accord_en_français
    if t_node.template_name.startswith("en-adj"):
        process_en_adj_table(wxr, page_data[-1], t_node)
    elif t_node.template_name == "fro-adj":
        extract_fro_adj_template(wxr, page_data[-1], t_node)
    else:
        process_inflection_table(wxr, page_data, t_node)


IGNORE_TABLE_HEADERS = frozenset(
    {
        "terme",  # https://fr.wiktionary.org/wiki/Modèle:de-adj
        "forme",  # br-flex-adj
        "temps",  # en-conj-rég,
        "cas",  # lt_décl_as, ro-nom-tab(lower case)
        "commun",  # sv-nom-c-ar
        "personne",  # hu-pos-otok
        "pronom personnel",  # it-enclise
        "mutation",  # br-nom
        "nombre",  # ca-accord-mixte2
        "nature",  # de-adj
        "genre",  # es-accord-oa
        "conjugaison présent indicatif",  # avk-tab-conjug
        "mode",  # eo-conj
        "avec suffixes possessifs",  # fi-décl-valo
        "en kurmandji",  # flex-ku-nomf
    }
)
IGNORE_TABLE_HEADER_PREFIXES = (
    "voir la conjugaison du verbe ",  # Modèle:fr-verbe-flexion
    "conjugaison de ",  # sv-conj-ar
    "déclinaison de ",  # da-adj
)
IGNORE_TABLE_CELL = frozenset(
    {
        "Déclinaisons",  # de-adj
        "—",  # https://fr.wiktionary.org/wiki/Modèle:vls-nom
    }
)
IGNORE_TABLE_CELL_PREFIXES = (
    "voir conjugaison ",  # en-conj, avk-conj
)


@dataclass
class TableHeader:
    text: str
    index: int
    span: int


def table_data_cell_is_header(
    wxr: WiktextractContext, cell_node: WikiNode, page_title: str
) -> bool:
    # first child is bold node
    if cell_node.kind == NodeKind.TABLE_CELL:
        for child in cell_node.filter_empty_str_child():
            cell_text = clean_node(wxr, None, child)
            return (
                isinstance(child, WikiNode)
                and child.kind == NodeKind.BOLD
                and len(cell_text) > 0
                and cell_text[0].isupper()
                and cell_text != page_title
            )

    return False


def process_inflection_table(
    wxr: WiktextractContext, page_data: list[WordEntry], t_node: TemplateNode
) -> None:
    from .form_line import is_conj_link, process_conj_link_node

    expanded_node = wxr.wtp.parse(
        wxr.wtp.node_to_wikitext(t_node), expand_all=True
    )
    table_nodes = list(expanded_node.find_child(NodeKind.TABLE))
    if len(table_nodes) == 0:
        return
    table_node = table_nodes[0]
    column_headers = []
    rowspan_headers = []
    colspan_headers = []
    for row_num, table_row in enumerate(
        table_node.find_child(NodeKind.TABLE_ROW)
    ):
        # filter empty table cells
        table_row_nodes = [
            row_node_child
            for row_node_child in table_row.children
            if isinstance(row_node_child, WikiNode)
            and (
                row_node_child.kind == NodeKind.TABLE_HEADER_CELL
                or (
                    row_node_child.kind == NodeKind.TABLE_CELL
                    and len(list(row_node_child.filter_empty_str_child())) > 0
                )
            )
            and row_node_child.attrs.get("style") != "display:none"
            and "invisible" not in row_node_child.attrs.get("class", "")
        ]
        current_row_has_data_cell = any(
            isinstance(cell, WikiNode)
            and cell.kind == NodeKind.TABLE_CELL
            and not table_data_cell_is_header(wxr, cell, page_data[-1].word)
            for cell in table_row_nodes
        )
        if not current_row_has_data_cell:
            column_headers.clear()
        row_headers = []
        new_rowspan_headers = []
        for rowspan_text, rowspan_count in rowspan_headers:
            row_headers.append(rowspan_text)
            if rowspan_count - 1 > 0:
                new_rowspan_headers.append((rowspan_text, rowspan_count - 1))
        rowspan_headers = new_rowspan_headers

        column_cell_index = 0
        for column_num, table_cell in enumerate(table_row_nodes):
            form_data = Form()
            if isinstance(table_cell, WikiNode):
                if (
                    table_cell.kind == NodeKind.TABLE_HEADER_CELL
                    or table_data_cell_is_header(
                        wxr, table_cell, page_data[-1].word
                    )
                ):
                    if any(
                        table_cell.find_html(
                            "span",
                            attr_name="class",
                            attr_value="ligne-de-forme",
                        )
                    ):
                        # ignore gender header in template "ro-nom-tab"
                        continue
                    table_header_text = clean_node(
                        wxr, None, table_cell
                    ).replace("\n", " ")
                    if (
                        table_header_text.lower() in IGNORE_TABLE_HEADERS
                        or table_header_text.lower().startswith(
                            IGNORE_TABLE_HEADER_PREFIXES
                        )
                        or len(table_header_text.strip()) == 0
                    ):
                        continue
                    rsplit_header = table_header_text.rsplit(maxsplit=1)
                    if len(rsplit_header) > 1 and rsplit_header[-1].isdecimal():
                        # "Pluriel 1" in template "br-nom"
                        table_header_text = rsplit_header[0]

                    if not current_row_has_data_cell:
                        # if all cells of the row are header cells
                        # then the header cells are column headers
                        if "colspan" in table_cell.attrs:
                            colspan_headers.append(
                                TableHeader(
                                    table_header_text,
                                    column_cell_index,
                                    int(table_cell.attrs.get("colspan")),
                                )
                            )
                        else:
                            column_headers.append(table_header_text)
                        column_cell_index += int(
                            table_cell.attrs.get("colspan", 1)
                        )
                    else:
                        if table_header_text not in row_headers:
                            row_headers.append(table_header_text)
                        if "rowspan" in table_cell.attrs:
                            rowspan_headers.append(
                                (
                                    table_header_text,
                                    int(table_cell.attrs.get("rowspan")) - 1,
                                )
                            )
                elif table_cell.kind == NodeKind.TABLE_CELL:
                    has_conj_link = False
                    for link_node in table_cell.find_child(NodeKind.LINK):
                        if is_conj_link(wxr, link_node):
                            process_conj_link_node(wxr, link_node, page_data)
                            has_conj_link = True
                            break
                    if has_conj_link:
                        continue
                    table_cell_lines = clean_node(wxr, None, table_cell)
                    for table_cell_line in table_cell_lines.splitlines():
                        if is_ipa_text(table_cell_line):
                            insert_ipa(form_data, table_cell_line)
                        elif (
                            table_cell_line != page_data[-1].word
                            and table_cell_line not in IGNORE_TABLE_CELL
                            and not table_cell_line.lower().startswith(
                                IGNORE_TABLE_CELL_PREFIXES
                            )
                        ):
                            if form_data.form == "":
                                form_data.form = table_cell_line
                            else:
                                form_data.form += "\n" + table_cell_line
                    for colspan_header in colspan_headers:
                        if (
                            column_cell_index >= colspan_header.index
                            and column_cell_index
                            < colspan_header.index + colspan_header.span
                        ):
                            form_data.raw_tags.append(colspan_header.text)
                    if (
                        "colspan" not in table_cell.attrs
                        and len(column_headers) > column_cell_index
                        and column_headers[column_cell_index].lower()
                        not in IGNORE_TABLE_HEADERS
                    ):
                        form_data.raw_tags.append(
                            column_headers[column_cell_index]
                        )

                    if len(row_headers) > 0:
                        form_data.raw_tags.extend(row_headers)
                    if form_data.form != "":
                        for form in form_data.form.splitlines():
                            if form.startswith("(") and form.endswith(")"):
                                form_data.raw_tags.append(form.strip("()"))
                                continue
                            new_form_data = form_data.model_copy(deep=True)
                            new_form_data.form = form.removeprefix("ou ")
                            translate_raw_tags(
                                new_form_data, t_node.template_name
                            )
                            if len(new_form_data.form.strip()) > 0:
                                page_data[-1].forms.append(new_form_data)

                    colspan_text = table_cell.attrs.get("colspan", "1")
                    if colspan_text.isdecimal():
                        column_cell_index += int(colspan_text)


def split_ipa(text: str) -> list[str]:
    # break IPA text if it contains "ou"(or)
    if " ou " in text:
        # two ipa texts in the same line: "en-conj-rég" template
        return text.split(" ou ")
    if text.startswith("ou "):
        return [text.removeprefix("ou ")]
    if text.endswith("Prononciation ?\\"):
        # inflection table templates use a edit link when the ipa data is
        # missing, and the link usually ends with "Prononciation ?"
        return []
    return [text]


def insert_ipa(form: Form, ipa_text: str) -> None:
    ipa_data = split_ipa(ipa_text)
    if len(ipa_data) == 0:
        return
    form.ipas.extend(ipa_data)


def process_en_adj_table(
    wxr: WiktextractContext, word_entry: WordEntry, t_node: WikiNode
) -> None:
    # https://fr.wiktionary.org/wiki/Modèle:en-adj
    # and other en-adj* templates
    # these templates use normal table cell for column table header
    expanded_node = wxr.wtp.parse(
        wxr.wtp.node_to_wikitext(t_node), expand_all=True
    )
    table_nodes = list(expanded_node.find_child(NodeKind.TABLE))
    if len(table_nodes) == 0:
        return
    table_node = table_nodes[0]
    for row_num, table_row in enumerate(
        table_node.find_child(NodeKind.TABLE_ROW)
    ):
        if row_num == 0:
            # skip header
            continue
        if len(table_row.children) > 1:
            form_data = Form()
            form_data.raw_tags.append(
                clean_node(wxr, None, table_row.children[0])
            )
            form_text = clean_node(wxr, None, table_row.children[1])
            for form_line in form_text.splitlines():
                if form_line in IGNORE_TABLE_CELL:
                    continue
                elif is_ipa_text(form_line):
                    insert_ipa(form_data, form_line)
                else:
                    form_data.form = form_line
            if form_data.form != word_entry.word and len(form_data.form) > 0:
                translate_raw_tags(form_data)
                word_entry.forms.append(form_data)


def extract_fro_adj_template(
    wxr: WiktextractContext, word_entry: WordEntry, t_node: TemplateNode
):
    # https://fr.wiktionary.org/wiki/Modèle:fro-adj
    expanded_node = wxr.wtp.parse(
        wxr.wtp.node_to_wikitext(t_node), expand_all=True
    )
    col_headers = []
    row_headers = []
    for table in expanded_node.find_child(NodeKind.TABLE):
        for row_index, row in enumerate(table.find_child(NodeKind.TABLE_ROW)):
            row_has_data = row.contain_node(NodeKind.TABLE_CELL)
            for col_index, cell_node in enumerate(
                row.find_child(NodeKind.TABLE_HEADER_CELL)
            ):
                cell_text = clean_node(wxr, None, cell_node)
                if cell_text == "" or cell_text.lower() in IGNORE_TABLE_HEADERS:
                    continue
                if not row_has_data:
                    col_headers.append(cell_text)
                else:
                    rowspan_str = cell_node.attrs.get("rowspan", "1")
                    rowspan = 1
                    if re.fullmatch(r"\d+", rowspan_str) is not None:
                        rowspan = int(rowspan_str)
                    row_headers.append(
                        TableHeader(cell_text, row_index, rowspan)
                    )

        for row_index, row in enumerate(table.find_child(NodeKind.TABLE_ROW)):
            for col_index, cell_node in enumerate(
                row.find_child(NodeKind.TABLE_CELL)
            ):
                cell_text = clean_node(wxr, None, cell_node)
                if cell_text in ["", wxr.wtp.title]:
                    continue
                form = Form(form=cell_text)
                if col_index < len(col_headers):
                    form.raw_tags.append(col_headers[col_index])
                rowspan_str = cell_node.attrs.get("rowspan", "1")
                rowspan = 1
                if re.fullmatch(r"\d+", rowspan_str) is not None:
                    rowspan = int(rowspan_str)
                for header in row_headers:
                    if (
                        header.index < row_index + rowspan
                        and row_index < header.index + header.span
                        and header.text not in form.raw_tags
                    ):
                        form.raw_tags.append(header.text)
                translate_raw_tags(form)
                word_entry.forms.append(form)
