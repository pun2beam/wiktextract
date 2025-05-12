import unittest

from wikitextprocessor import Wtp

from wiktextract.config import WiktionaryConfig
from wiktextract.extractor.ru.example import process_example_template
from wiktextract.extractor.ru.gloss import extract_gloss
from wiktextract.extractor.ru.models import Sense, WordEntry
from wiktextract.wxr_context import WiktextractContext


class TestRUExample(unittest.TestCase):
    def setUp(self) -> None:
        self.wxr = WiktextractContext(
            Wtp(lang_code="ru"),
            WiktionaryConfig(dump_file_lang_code="ru"),
        )

    def tearDown(self) -> None:
        self.wxr.wtp.close_db_conn()

    def get_default_sense_data(self) -> Sense:
        return Sense()

    def test_ru_extract_example(self):
        test_cases = [
            # Ignores empty template
            {"input": "{{пример|}}", "expected": []},
            # https://ru.wiktionary.org/wiki/Красная_Шапочка
            {
                "input": "{{пример|Недолго думая, отправляю овощ в рот.|М. И. Саитов|Островки||Бельские Просторы|2010|источник=НКРЯ}}",
                "expected": [
                    {
                        "author": "М. И. Саитов",
                        "collection": "Бельские Просторы",
                        "date_published": "2010",
                        "source": "НКРЯ",
                        "title": "Островки",
                        "text": "Недолго думая, отправляю овощ в рот.",
                    }
                ],
            },
            # https://ru.wiktionary.org/wiki/house
            {
                "input": "{{пример|This is my house and my family’s ancestral home.||перевод=Это мой дом и поселение моих семейных предков.}}",
                "expected": [
                    {
                        "text": "This is my house and my family’s ancestral home.",
                        "translation": "Это мой дом и поселение моих семейных предков.",
                    }
                ],
            },
        ]

        for case in test_cases:
            with self.subTest(case=case):
                self.wxr.wtp.start_page("")
                sense_data = self.get_default_sense_data()

                root = self.wxr.wtp.parse(case["input"])

                process_example_template(self.wxr, sense_data, root.children[0])

                examples = [
                    e.model_dump(exclude_defaults=True)
                    for e in sense_data.examples
                ]
                self.assertEqual(examples, case["expected"])

    def test_en_surname(self):
        self.wxr.wtp.add_page(
            "Шаблон:пример",
            10,
            """<span class="example-fullblock ">&#9670;&nbsp;<span class="example-block" style="color:darkgreen">This is Mister <b class="example-select" style="background-color: #EDF0FF; font-weight: bold;">Abad</b><span class="example-translate" style="color:grey">&#160;—&#32;Это мистер <b class="example-select" style="background-color: #EDF0FF; font-weight: bold;">Abad</b></span> <span class="example-details" style="font-size:smaller;"> <i><span class="citation-source"> </span></i></span></span></span>""",
        )
        self.wxr.wtp.add_page(
            "Шаблон:english surname example",
            10,
            "{{пример|This is Mister {{PAGENAME}}|перевод=Это мистер {{PAGENAME}}}}",
        )
        self.wxr.wtp.start_page("Abad")
        root = self.wxr.wtp.parse(
            """==== Значение ====
# (английская [[фамилия]]) {{english surname example}}"""
        )
        word_entry = WordEntry(
            lang="Английский", lang_code="en", pos="prop", word="Abad"
        )
        extract_gloss(self.wxr, word_entry, root.children[0])
        data = word_entry.model_dump(exclude_defaults=True)
        self.assertEqual(
            data["senses"][0],
            {
                "glosses": ["(английская фамилия)"],
                "examples": [
                    {
                        "text": "This is Mister Abad",
                        "bold_text_offsets": [(15, 19)],
                        "translation": "Это мистер Abad",
                        "bold_translation_offsets": [(11, 15)],
                    }
                ],
            },
        )

    def test_ref_field(self):
        self.wxr.wtp.start_page("плыть")
        self.wxr.wtp.add_page(
            "Шаблон:пример",
            10,
            '<span class="example-fullblock ">&#9670;&nbsp;<span class="example-block" style="color:darkgreen">На красных лапках гусь тяжелый, задумав <span class="example-select" style="background-color: #EDF0FF; font-weight: bold;">плыть</span> по лону вод, ступает бережно на лёд. <span class="example-details" style="font-size:smaller;"> <i>[[w:Пушкин, Александр Сергеевич|А. С. Пушкин]], «Записные книжки», <span class="example-date">1815-1836</span>&nbsp;гг.<span class="citation-source"> <span class="nkrja-source" style="font-size: x-small; ">&#91;[[w:Национальный корпус русского языка|НКРЯ]]&#93;</span></span></i></span></span></span>',
        )
        root = self.wxr.wtp.parse(
            "{{пример|На красных лапках гусь тяжелый, задумав {{выдел|плыть}} по лону вод, ступает бережно на лёд.|Пушкин|Записные книжки|1815-1836|источник=НКРЯ}}"
        )
        sense = Sense()
        process_example_template(self.wxr, sense, root.children[0])
        self.assertEqual(
            sense.examples[0].ref,
            "А. С. Пушкин, «Записные книжки», 1815-1836 гг. [НКРЯ]",
        )
