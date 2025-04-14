from unittest import TestCase

from wikitextprocessor import Wtp

from wiktextract.config import WiktionaryConfig
from wiktextract.extractor.ko.page import parse_page
from wiktextract.wxr_context import WiktextractContext


class TestKoExample(TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.wxr = WiktextractContext(
            Wtp(lang_code="ko"),
            WiktionaryConfig(
                dump_file_lang_code="ko",
                capture_language_codes=None,
            ),
        )

    def tearDown(self) -> None:
        self.wxr.wtp.close_db_conn()

    def test_ja_ruby(self):
        self.wxr.wtp.add_page(
            "틀:r", 10, "<ruby><rb>{{{1}}}</rb><rt>{{{2}}}</rt></ruby>"
        )
        data = parse_page(
            self.wxr,
            "犬",
            """== 일본어 ==
=== 명사 ===
* '''1.''' [[개]].
:* {{lang|ja|どの{{r|'''犬'''|いぬ}}が{{r|彼女|かのじょ}}のですか。—あの{{r|大|おお}}きい{{r|犬|いぬ}}です。}} 어느 쪽 개가 그 여자의 것입니까? — 저 큰 개입니다.""",
        )
        self.assertEqual(
            data[0]["senses"][0]["examples"][0],
            {
                "text": "どの犬が彼女のですか。—あの大きい犬です。",
                "ruby": [
                    ("犬", "いぬ"),
                    ("彼女", "かのじょ"),
                    ("大", "おお"),
                    ("犬", "いぬ"),
                ],
                "translation": "어느 쪽 개가 그 여자의 것입니까? — 저 큰 개입니다.",
            },
        )

    def test_zh(self):
        data = parse_page(
            self.wxr,
            "大家",
            """== 중국어 ==
* '''1.''' 모든 [[사람]], [[모두]], 사람들
: {{lang|zh|聖春問'''大家'''/聖春问'''大家'''  (Shèng chūn wèn dàjiā) }} 성춴은 모두에게 물었다.""",
        )
        self.assertEqual(
            data[0]["senses"][0]["examples"],
            [
                {
                    "text": "聖春問大家",
                    "bold_text_offsets": [(3, 5)],
                    "roman": "Shèng chūn wèn dàjiā",
                    "tags": ["Traditional Chinese"],
                    "translation": "성춴은 모두에게 물었다.",
                },
                {
                    "text": "聖春问大家",
                    "bold_text_offsets": [(3, 5)],
                    "roman": "Shèng chūn wèn dàjiā",
                    "tags": ["Simplified Chinese"],
                    "translation": "성춴은 모두에게 물었다.",
                },
            ],
        )

    def test_ref_quote_template(self):
        self.wxr.wtp.add_page(
            "틀:따옴삼국지",
            10,
            "3세기, 진수,《삼국지》, 〈권30 위서 오환선비동이전 (魏書 烏丸鮮卑東夷傳)〉",
        )
        data = parse_page(
            self.wxr,
            "犬",
            """== 한자 ==
=== 의미 ===
* '''1.''' (동물) [[개]].
:* 肥養犬 개를 살찌게 기르다. {{따옴삼국지|30|30 위서 오환선비동이전 (魏書 烏丸鮮卑東夷傳)}}""",
        )
        self.assertEqual(
            data[0]["senses"][0]["examples"][0],
            {
                "text": "肥養犬 개를 살찌게 기르다.",
                "ref": "3세기, 진수,《삼국지》, 〈권30 위서 오환선비동이전 (魏書 烏丸鮮卑東夷傳)〉",
            },
        )

    def test_ja_ux_template(self):
        self.wxr.wtp.add_page(
            "틀:ux",
            10,
            """<div><span lang="ja" class="Jpan"><ruby>阿<rp>(</rp><rt>あ</rt><rp>)</rp></ruby><ruby>吽<rp>(</rp><rt>うん</rt><rp>)</rp></ruby>の'''<ruby>呼<rp>(</rp><rt>こ</rt><rp>)</rp></ruby><ruby>吸<rp>(</rp><rt>きゅう</rt><rp>)</rp></ruby>'''</span></div><dl><dd><i><span class="tr">aun no '''kokyū'''</span></i></dd><dd>찰떡'''호흡'''</dd><dd>(literally, “아흠의 '''호흡'''”)</dd></dl>[[분류:일본어 용례가 포함된 낱말|呼吸]]""",
        )
        data = parse_page(
            self.wxr,
            "呼吸",
            """== 일본어 ==
=== 명사 ===
# [[조화]], [[호흡]]
#: {{ux|ja|阿%吽の'''呼%吸'''|あ%うん の '''こ%きゅう'''|찰떡'''호흡'''|lit=아흠의 '''호흡'''}}""",
        )
        self.assertEqual(
            data[0]["senses"][0]["examples"][0],
            {
                "text": "阿吽の呼吸",
                "bold_text_offsets": [(3, 5)],
                "ruby": [
                    ("阿", "あ"),
                    ("吽", "うん"),
                    ("呼", "こ"),
                    ("吸", "きゅう"),
                ],
                "roman": "aun no kokyū",
                "bold_roman_offsets": [(7, 12)],
                "translation": "찰떡호흡",
                "bold_translation_offsets": [(2, 4)],
                "literal_meaning": "아흠의 호흡",
                "bold_literal_offsets": [(4, 6)],
            },
        )
        self.assertEqual(
            data[0]["senses"][0]["categories"], ["일본어 용례가 포함된 낱말"]
        )

    def test_ko_ux_template(self):
        self.wxr.wtp.add_page(
            "틀:예문",
            10,
            """<div class="h-usage-example"><span class="None" lang="ko"><span style="font-size: 120%25">미리 밝혀둘 것도 없이 마크 로스코와 나는 아무 관계도 '''없다'''</span></span><dl><dd>(<span class="e-source">한강의 시, 〈마크 로스코와 나〉</span>)</dd><dd><span class="e-footer">화자와 마크 로스크는 서로 관계가 없음</span></dd></dl></div>[[Category:한국어 용례가 포함된 낱말|없다]]""",
        )
        data = parse_page(
            self.wxr,
            "없다",
            """== 한국어 ==
=== 형용사 ===
# 무엇이 그러하지 않다.
#:{{예문|ko|미리 밝혀둘 것도 없이 마크 로스코와 나는 아무 관계도 '''없다'''|footer=화자와 마크 로스크는 서로 관계가 없음|출처 = 한강의 시, 〈마크 로스코와 나〉}}""",
        )
        self.assertEqual(
            data[0]["senses"][0]["examples"][0],
            {
                "text": "미리 밝혀둘 것도 없이 마크 로스코와 나는 아무 관계도 없다",
                "bold_text_offsets": [(31, 33)],
                "note": "화자와 마크 로스크는 서로 관계가 없음",
                "ref": "한강의 시, 〈마크 로스코와 나〉",
            },
        )
        self.assertEqual(
            data[0]["senses"][0]["categories"], ["한국어 용례가 포함된 낱말"]
        )

    def test_jibong_yuseol_template(self):
        self.wxr.wtp.add_page(
            "틀:지봉유설",
            10,
            """'''1614년''', [[:w:이수광|이수광]], 《[[:s:지봉유설|지봉유설]]》, 〈[[:s:지봉유설/2권|2권 外國 條]]〉""",
        )
        data = parse_page(
            self.wxr,
            "없다",
            """== 중국어 ==
====명사====
# [[동서]].
#: {{지봉유설|2|2권 外國 條}}
#:: {{lang|zh|'''東西'''六十日程}} 동서로 60일이 걸리는 거리이다.""",
        )
        self.assertEqual(
            data[0]["senses"][0]["examples"][0],
            {
                "text": "東西六十日程",
                "bold_text_offsets": [(0, 2)],
                "translation": "동서로 60일이 걸리는 거리이다.",
                "ref": "1614년, 이수광, 《지봉유설》, 〈2권 外國 條〉",
            },
        )

    def test_sound_file(self):
        data = parse_page(
            self.wxr,
            "사람",
            """== 중국어 ==
=== 명사 ===
==== 명사 1 ====
# 어떤 지역이나 시기에 태어나거나 살고 있거나 살았던 자.
:* 한국 '''사람''' [[File:Ko-한국 사람.oga]]""",
        )
        self.assertEqual(
            data[0]["senses"][0]["examples"][0]["text"], "한국 사람"
        )
        self.assertEqual(
            data[0]["senses"][0]["examples"][0]["sounds"][0]["audio"],
            "Ko-한국 사람.oga",
        )

    def test_wrong_nested_list(self):
        data = parse_page(
            self.wxr,
            "들다",
            """== 중국어 ==
=== 명사 ===
==== 명사 1 ====
#  한 곳에서 다른 어디로 또는 밖에서 속이나 안으로 향해 가거나, 오거나 또는 어디에 자리하다.
: 안으로 드시지요.
:* 물이 어디에 '''들어''' 있어요？ [[File:물이 어디에 들어 있어요？.ogg]]""",
        )
        self.assertEqual(
            data[0]["senses"][0]["examples"][0]["text"], "안으로 드시지요."
        )
        self.assertTrue("sounds" not in data[0]["senses"][0]["examples"][0])
        self.assertEqual(
            data[0]["senses"][0]["examples"][1]["text"],
            "물이 어디에 들어 있어요？",
        )
        self.assertEqual(
            data[0]["senses"][0]["examples"][1]["bold_text_offsets"], [(7, 9)]
        )
        self.assertEqual(
            data[0]["senses"][0]["examples"][1]["sounds"][0]["audio"],
            "물이 어디에 들어 있어요？.ogg",
        )
