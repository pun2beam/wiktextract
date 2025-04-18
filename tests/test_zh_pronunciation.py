from unittest import TestCase

from wikitextprocessor import Wtp

from wiktextract.config import WiktionaryConfig
from wiktextract.extractor.zh.models import WordEntry
from wiktextract.extractor.zh.page import parse_page
from wiktextract.extractor.zh.pronunciation import extract_pronunciation_section
from wiktextract.wxr_context import WiktextractContext


class TestPronunciation(TestCase):
    maxDiff = None

    def setUp(self):
        self.wxr = WiktextractContext(
            Wtp(lang_code="zh"),
            WiktionaryConfig(
                capture_language_codes=None, dump_file_lang_code="zh"
            ),
        )

    def tearDown(self):
        self.wxr.wtp.close_db_conn()

    def test_homophone_table(self):
        self.wxr.wtp.start_page("大家")
        self.wxr.wtp.add_page(
            "Template:zh-pron",
            10,
            """* [[w:官話|官話]]
** <small>([[w:現代標準漢語|現代標準漢語]])</small>
*** <small>同音詞</small>：<table><tr><th>[展開/摺疊]</th></tr><tr><td><span class="Hani" lang="zh">[[大姑#漢語|大姑]]</span><br><span class="Hani" lang="zh">[[小姑#漢語|小姑]]</span></td></tr></table>
* [[w:晉語|晉語]]
** <small>([[w:太原話|太原話]])</sup></small>
*** <small>[[Wiktionary:國際音標|國際音標]] (老派)</small>：<span class="IPA">/sz̩⁵³/</span>
            """,
        )
        root = self.wxr.wtp.parse("{{zh-pron}}")
        base_data = WordEntry(
            word="大家", lang_code="zh", lang="漢語", pos="noun"
        )
        extract_pronunciation_section(self.wxr, base_data, root)
        self.assertEqual(
            [d.model_dump(exclude_defaults=True) for d in base_data.sounds],
            [
                {
                    "homophone": "大姑",
                    "tags": ["Mandarin", "Standard Chinese"],
                    "raw_tags": ["同音詞"],
                },
                {
                    "homophone": "小姑",
                    "tags": ["Mandarin", "Standard Chinese"],
                    "raw_tags": ["同音詞"],
                },
                {
                    "ipa": "/sz̩⁵³/",
                    "tags": ["Jin"],
                    "raw_tags": ["太原話", "國際音標 (老派)"],
                },
            ],
        )

    def test_homophone_template(self):
        self.wxr.wtp.start_page("大家")
        root = self.wxr.wtp.parse("* {{homophones|ja|大矢|大宅|大谷}}")
        base_data = WordEntry(
            word="大家", lang_code="ja", lang="日語", pos="noun"
        )
        extract_pronunciation_section(self.wxr, base_data, root)
        self.assertEqual(
            [d.model_dump(exclude_defaults=True) for d in base_data.sounds],
            [
                {"homophone": "大矢"},
                {"homophone": "大宅"},
                {"homophone": "大谷"},
            ],
        )

    def test_en_pron_list(self):
        self.wxr.wtp.start_page("hello")
        self.wxr.wtp.add_page("Template:a", 10, "(美國)")
        root = self.wxr.wtp.parse(
            "* {{a|US}} {{enPR|hĕ-lō'|hə-lō'}}、{{IPA|en|/hɛˈloʊ/|/həˈloʊ/|/ˈhɛloʊ/}}"
        )
        base_data = WordEntry(
            word="hello", lang_code="en", lang="英語", pos="intj"
        )
        extract_pronunciation_section(self.wxr, base_data, root)
        self.assertEqual(
            [d.model_dump(exclude_defaults=True) for d in base_data.sounds],
            [
                {"enpr": "hĕ-lō'", "raw_tags": ["美國"]},
                {"enpr": "hə-lō'", "raw_tags": ["美國"]},
                {"ipa": "/hɛˈloʊ/", "raw_tags": ["美國"]},
                {"ipa": "/həˈloʊ/", "raw_tags": ["美國"]},
                {"ipa": "/ˈhɛloʊ/", "raw_tags": ["美國"]},
            ],
        )

    def test_level3_pron_level3_pos(self):
        self.wxr.wtp.add_page(
            "Template:zh-pron",
            10,
            """<div><div>
* [[w:官話|官話]]
*:<small>([[w:漢語拼音|拼音]])</small>：<span>[[chōng'ěr]]</span>
</div></div>[[Category:有國際音標的漢語詞|儿04耳00]]""",
        )
        self.wxr.wtp.add_page(
            "Template:zh-verb",
            10,
            "充耳[[Category:漢語詞元|儿04耳00]][[Category:漢語動詞|儿04耳00]]",
        )
        self.wxr.wtp.add_page(
            "Template:head",
            10,
            "充耳[[Category:漢語詞元|儿04耳00]][[Category:漢語名詞|儿04耳00]]",
        )
        self.assertEqual(
            parse_page(
                self.wxr,
                "充耳",
                """==漢語==
===發音===
{{zh-pron
|m=chōng'ěr
|cat=v,n
}}

===動詞===
{{zh-verb}}

# [[塞住]][[耳朵]]

===名詞===
{{head|zh|名詞}}

# 古[[冠冕]]旁的[[瑱]]玉，因其[[下垂]]及耳，而得名""",
            ),
            [
                {
                    "categories": [
                        "有國際音標的漢語詞",
                        "漢語詞元",
                        "漢語動詞",
                    ],
                    "lang": "漢語",
                    "lang_code": "zh",
                    "pos": "verb",
                    "pos_title": "動詞",
                    "senses": [{"glosses": ["塞住耳朵"]}],
                    "sounds": [
                        {"zh_pron": "chōng'ěr", "tags": ["Mandarin", "Pinyin"]}
                    ],
                    "word": "充耳",
                },
                {
                    "categories": [
                        "有國際音標的漢語詞",
                        "漢語詞元",
                        "漢語名詞",
                    ],
                    "lang": "漢語",
                    "lang_code": "zh",
                    "pos": "noun",
                    "pos_title": "名詞",
                    "senses": [
                        {"glosses": ["古冠冕旁的瑱玉，因其下垂及耳，而得名"]}
                    ],
                    "sounds": [
                        {"zh_pron": "chōng'ěr", "tags": ["Mandarin", "Pinyin"]}
                    ],
                    "word": "充耳",
                },
            ],
        )

    def test_level3_pron_level4_pos(self):
        self.wxr.wtp.add_page(
            "Template:zh-pron",
            10,
            """<div><div>
* [[w:官話|官話]]
*:<small>([[w:漢語拼音|拼音]])</small>：<span>[[{{{m}}}]]</span>
</div></div>""",
        )
        self.assertEqual(
            parse_page(
                self.wxr,
                "大家",
                """==漢語==
===發音1===
{{zh-pron
|m=dàjiā, dà'ā
|cat=n
}}

====名詞====

# [[眾人]]，某個[[範圍]]中[[所有]]的[[人]]

===發音2===
{{zh-pron
|m=dàjiā
|cat=n
}}

====名詞====

# [[卿大夫]]之[[家]]

===發音3===
{{zh-pron
|m=dàgū
|cat=n
}}

====名詞====

# 對[[女子]]的[[尊稱]]""",
            ),
            [
                {
                    "lang": "漢語",
                    "lang_code": "zh",
                    "pos": "noun",
                    "pos_title": "名詞",
                    "senses": [{"glosses": ["眾人，某個範圍中所有的人"]}],
                    "sounds": [
                        {
                            "zh_pron": "dàjiā, dà'ā",
                            "tags": ["Mandarin", "Pinyin"],
                        }
                    ],
                    "word": "大家",
                },
                {
                    "lang": "漢語",
                    "lang_code": "zh",
                    "pos": "noun",
                    "pos_title": "名詞",
                    "senses": [{"glosses": ["卿大夫之家"]}],
                    "sounds": [
                        {"zh_pron": "dàjiā", "tags": ["Mandarin", "Pinyin"]}
                    ],
                    "word": "大家",
                },
                {
                    "lang": "漢語",
                    "lang_code": "zh",
                    "pos": "noun",
                    "pos_title": "名詞",
                    "senses": [{"glosses": ["對女子的尊稱"]}],
                    "sounds": [
                        {"zh_pron": "dàgū", "tags": ["Mandarin", "Pinyin"]}
                    ],
                    "word": "大家",
                },
            ],
        )
