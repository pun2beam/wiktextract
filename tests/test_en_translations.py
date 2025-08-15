# Tests for parse_translation_desc()
#
# Copyright (c) 2021 Tatu Ylonen.  See file LICENSE and https://ylonen.org

import unittest

from wikitextprocessor import Wtp

from wiktextract.config import WiktionaryConfig
from wiktextract.extractor.en.form_descriptions import parse_translation_desc
from wiktextract.extractor.en.translations import parse_translation_item_text
from wiktextract.thesaurus import close_thesaurus_db
from wiktextract.wxr_context import WiktextractContext


class EnTrTests(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.wxr = WiktextractContext(Wtp(), WiktionaryConfig())
        # Note: some tests use last char
        self.wxr.wtp.start_page("abolitionism")
        self.wxr.wtp.start_section("English")

    def tearDown(self) -> None:
        self.wxr.wtp.close_db_conn()
        close_thesaurus_db(
            self.wxr.thesaurus_db_path, self.wxr.thesaurus_db_conn
        )

    def runtr(
        self,
        item,
        sense=None,
        pos_datas=None,
        lang=None,
        langcode=None,
        translations_from_template=None,
        is_reconstruction=False,
    ):
        """Simple test runner.  Returns data."""
        if pos_datas is None:
            pos_datas = []
        if translations_from_template is None:
            translations_from_template = []
        data = {}
        parse_translation_item_text(
            self.wxr,
            self.wxr.wtp.title,
            data,
            item,
            sense,
            lang,
            langcode,
            translations_from_template,
            is_reconstruction,
        )
        return data

    def test_trdesc1(self):
        tr = {}
        # Note: this test uses last char of title
        parse_translation_desc(self.wxr, "French", "abolitionnisme m", tr)
        self.assertEqual(self.wxr.wtp.errors, [])
        self.assertEqual(self.wxr.wtp.warnings, [])
        self.assertEqual(self.wxr.wtp.debugs, [])
        self.assertEqual(tr, {"word": "abolitionnisme", "tags": ["masculine"]})

    def test_trdesc2(self):
        tr = {}
        parse_translation_desc(self.wxr, "French", "abolitionnisme f", tr)
        self.assertEqual(self.wxr.wtp.errors, [])
        self.assertEqual(self.wxr.wtp.warnings, [])
        self.assertEqual(self.wxr.wtp.debugs, [])
        self.assertEqual(tr, {"word": "abolitionnisme", "tags": ["feminine"]})

    def test_trdesc3(self):
        tr = {}
        # m is in page title, should not interpret as tag
        self.wxr.wtp.start_page("m m m")
        parse_translation_desc(self.wxr, "French", "m m m", tr)
        self.assertEqual(self.wxr.wtp.errors, [])
        self.assertEqual(self.wxr.wtp.warnings, [])
        self.assertEqual(self.wxr.wtp.debugs, [])
        self.assertEqual(tr, {"word": "m m m"})

    def test_trdesc4(self):
        tr = {}
        self.wxr.wtp.start_page("assessment")
        parse_translation_desc(self.wxr, "German", "Schätzung f", tr)
        self.assertEqual(self.wxr.wtp.errors, [])
        self.assertEqual(self.wxr.wtp.warnings, [])
        self.assertEqual(self.wxr.wtp.debugs, [])
        self.assertEqual(tr, {"word": "Schätzung", "tags": ["feminine"]})

    def test_tr1(self):
        data = self.runtr("Finnish: foo")
        self.assertEqual(
            data,
            {
                "translations": [
                    {
                        "word": "foo",
                        "lang": "Finnish",
                        "code": "fi",  # DEPRECATED for "lang_code"
                        "lang_code": "fi",
                    },
                ]
            },
        )

    def test_tr2(self):
        data = self.runtr("Swedish: foo f")
        self.assertEqual(
            data,
            {
                "translations": [
                    {
                        "word": "foo",
                        "lang": "Swedish",
                        "code": "sv",  # DEPRECATED for "lang_code"
                        "lang_code": "sv",
                        "tags": ["feminine"],
                    },
                ]
            },
        )

    def test_tr3(self):
        data = self.runtr("Swedish: foo f or m")
        self.assertEqual(
            data,
            {
                "translations": [
                    {
                        "word": "foo",
                        "lang": "Swedish",
                        "code": "sv",  # DEPRECATED for "lang_code"
                        "lang_code": "sv",
                        "tags": ["feminine", "masculine"],
                    },
                ]
            },
        )

    def test_tr4(self):
        data = self.runtr("Swedish: foo ?")
        self.assertEqual(
            data,
            {
                "translations": [
                    {
                        "word": "foo",
                        "lang": "Swedish",
                        "code": "sv",  # DEPRECATED for "lang_code"
                        "lang_code": "sv",
                    },
                ]
            },
        )

    def test_tr5(self):
        data = self.runtr("Swedish: foo f, bar m")
        self.assertEqual(
            data,
            {
                "translations": [
                    {
                        "word": "foo",
                        "lang": "Swedish",
                        "code": "sv",  # DEPRECATED for "lang_code"
                        "lang_code": "sv",
                        "tags": ["feminine"],
                    },
                    {
                        "word": "bar",
                        "lang": "Swedish",
                        "code": "sv",  # DEPRECATED for "lang_code"
                        "lang_code": "sv",
                        "tags": ["masculine"],
                    },
                ]
            },
        )

    def test_tr6(self):
        data = self.runtr("Swedish: foo f sg or f pl")
        self.assertEqual(
            data,
            {
                "translations": [
                    {
                        "word": "foo",
                        "lang": "Swedish",
                        "code": "sv",  # DEPRECATED for "lang_code"
                        "lang_code": "sv",
                        "tags": ["feminine", "plural", "singular"],
                    },
                ]
            },
        )

    def test_tr7(self):
        # Dual should not be processed for Swedish
        data = self.runtr("Swedish: foo du")
        self.assertNotEqual(self.wxr.wtp.debugs, [])  # Should be suspicious tr
        self.assertEqual(
            data,
            {
                "translations": [
                    {
                        "word": "foo du",
                        "lang": "Swedish",
                        "code": "sv",  # DEPRECATED for "lang_code"
                        "lang_code": "sv",
                    },
                ]
            },
        )

    def test_tr8(self):
        data = self.runtr("Mandarin: 是 (rrr)", lang="Chinese")
        self.assertEqual(
            data,
            {
                "translations": [
                    {
                        "word": "是",
                        "roman": "rrr",
                        "lang": "Chinese Mandarin",
                        "code": "zh",  # DEPRECATED for "lang_code"
                        "lang_code": "zh",
                    }
                ]
            },
        )

    def test_tr9(self):
        data = self.runtr("Mandarin: 寺 (zh) (sì) (Buddhist)", langcode="zh")
        self.assertEqual(self.wxr.wtp.debugs, [])
        self.assertEqual(
            data,
            {
                "translations": [
                    {
                        "word": "寺",
                        "roman": "sì",
                        "lang": "Mandarin",
                        "code": "zh",  # DEPRECATED for "lang_code"
                        "lang_code": "zh",
                        "topics": [
                            "Buddhist",
                            "Buddhism",
                            "religion",
                            "lifestyle",
                        ],
                    },
                ]
            },
        )

    def test_tr10(self):
        data = self.runtr(
            "Arabic: مَعْبَد‎ m (maʿbad), هَيْكَل‎ m (haykal)", langcode="ar"
        )
        self.assertEqual(self.wxr.wtp.debugs, [])
        self.assertEqual(
            data,
            {
                "translations": [
                    {
                        "word": "مَعْبَد‎",
                        "roman": "maʿbad",
                        "lang": "Arabic",
                        "code": "ar",  # DEPRECATED for "lang_code"
                        "lang_code": "ar",
                        "tags": ["masculine"],
                    },
                    {
                        "word": "هَيْكَل‎",
                        "roman": "haykal",
                        "lang": "Arabic",
                        "code": "ar",  # DEPRECATED for "lang_code"
                        "lang_code": "ar",
                        "tags": ["masculine"],
                    },
                ]
            },
        )

    def test_tr11(self):
        data = self.runtr("Oriya: please add this translation if you can")
        self.assertEqual(self.wxr.wtp.debugs, [])
        self.assertEqual(data, {})

    def test_tr12(self):
        data = self.runtr(
            "Burmese: လျှောက် (my) (hlyauk), လမ်းလျှောက် (my) (lam:hlyauk)"
        )
        self.assertEqual(self.wxr.wtp.debugs, [])
        self.assertEqual(
            data,
            {
                "translations": [
                    {
                        "word": "လျှောက်",
                        "roman": "hlyauk",
                        "lang": "Burmese",
                        "code": "my",  # DEPRECATED for "lang_code"
                        "lang_code": "my",
                    },
                    {
                        "word": "လမ်းလျှောက်",
                        "roman": "lam:hlyauk",
                        "lang": "Burmese",
                        "code": "my",  # DEPRECATED for "lang_code"
                        "lang_code": "my",
                    },
                ]
            },
        )

    def test_tr13(self):
        data = self.runtr(
            "Finnish: tämä, testi", translations_from_template=["tämä, testi"]
        )
        self.assertEqual(self.wxr.wtp.debugs, [])
        self.assertEqual(
            data,
            {
                "translations": [
                    {
                        "word": "tämä, testi",
                        "lang": "Finnish",
                        "code": "fi",  # DEPRECATED for "lang_code"
                        "lang_code": "fi",
                    },
                ]
            },
        )

    def test_tr14(self):
        data = self.runtr(
            "Finnish: kävellä (fi), käydä (fi) " "(poetic or archaic)"
        )
        self.assertEqual(self.wxr.wtp.debugs, [])
        self.assertEqual(
            data,
            {
                "translations": [
                    {
                        "word": "kävellä",
                        "lang": "Finnish",
                        "code": "fi",  # DEPRECATED for "lang_code"
                        "lang_code": "fi",
                    },
                    {
                        "word": "käydä",
                        "lang": "Finnish",
                        "code": "fi",  # DEPRECATED for "lang_code"
                        "lang_code": "fi",
                        "tags": ["archaic", "poetic"],
                    },
                ]
            },
        )

    def test_tr15(self):
        data = self.runtr(
            "Macedonian: шета (šeta) (to go for a walk), " "иде (ide)"
        )
        self.assertEqual(self.wxr.wtp.debugs, [])
        self.assertEqual(
            data,
            {
                "translations": [
                    {
                        "word": "шета",
                        "roman": "šeta",
                        "lang": "Macedonian",
                        "english": "to go for a walk",  # DEPRECATED
                        "translation": "to go for a walk",
                        "code": "mk",  # DEPRECATED for "lang_code"
                        "lang_code": "mk",
                    },
                    {
                        "word": "иде",
                        "roman": "ide",
                        "lang": "Macedonian",
                        "code": "mk",  # DEPRECATED for "lang_code"
                        "lang_code": "mk",
                    },
                ]
            },
        )

    # This test wasn't being run because the name was reassigned
    # by the test below, and now it doesn't pass when re-enabled.
    def test_tr16(self):
        data = self.runtr(
            "Russian: испари́ться (ru) (isparítʹsja) "
            "(colloquial), бы́ли вы́несенны pl or pf "
            "(býli výnesenny) (past tense)"
        )
        self.assertEqual(self.wxr.wtp.debugs, [])
        self.assertEqual(
            data,
            {
                "translations": [
                    {
                        "word": "испари́ться",
                        "roman": "isparítʹsja",
                        "lang": "Russian",
                        "code": "ru",  # DEPRECATED for "lang_code"
                        "lang_code": "ru",
                        "tags": ["colloquial"],
                    },
                    {
                        "word": "бы́ли вы́несенны",
                        "roman": "býli výnesenny",
                        "lang": "Russian",
                        "code": "ru",  # DEPRECATED for "lang_code"
                        "lang_code": "ru",
                        "tags": [
                            "?plural",
                            "past",
                            "perfective",
                        ],
                    },
                ]
            },
        )

    def test_tr16b(self):
        # Test second-level "language" being script name
        data = self.runtr("Burmese: ပဏ္ဏ n (paṇṇa)", lang="Pali")
        self.assertEqual(self.wxr.wtp.debugs, [])
        self.assertEqual(
            data,
            {
                "translations": [
                    {
                        "word": "ပဏ္ဏ",
                        "roman": "paṇṇa",
                        "lang": "Pali",
                        "code": "pi",  # DEPRECATED for "lang_code"
                        "lang_code": "pi",
                        "tags": ["Burmese", "neuter"],
                    },
                ]
            },
        )

    def test_tr17(self):
        data = self.runtr("Finnish: foo 11")
        self.assertNotEqual(self.wxr.wtp.debugs, [])  # should get warning
        self.assertEqual(
            data,
            {
                "translations": [
                    {
                        "word": "foo 11",
                        "lang": "Finnish",
                        "code": "fi",  # DEPRECATED for "lang_code"
                        "lang_code": "fi",
                    },
                ]
            },
        )

    def test_tr18(self):
        data = self.runtr("Maore Comorian: wani 11 or 6")
        self.assertEqual(self.wxr.wtp.debugs, [])
        self.assertEqual(
            data,
            {
                "translations": [
                    {
                        "word": "wani",
                        "lang": "Maore Comorian",
                        "code": "swb",  # DEPRECATED for "lang_code"
                        "lang_code": "swb",
                        "tags": ["class-11", "class-6"],
                    },
                ]
            },
        )

    def test_tr19(self):
        data = self.runtr("Lingala: nkásá 9 or 10, lokásá 11 or 10")
        self.assertEqual(self.wxr.wtp.debugs, [])
        self.assertEqual(
            data,
            {
                "translations": [
                    {
                        "word": "nkásá",
                        "lang": "Lingala",
                        "code": "ln",  # DEPRECATED for "lang_code"
                        "lang_code": "ln",
                        "tags": ["class-10", "class-9"],
                    },
                    {
                        "word": "lokásá",
                        "lang": "Lingala",
                        "code": "ln",  # DEPRECATED for "lang_code"
                        "lang_code": "ln",
                        "tags": ["class-10", "class-11"],
                    },
                ]
            },
        )

    def test_tr20(self):
        data = self.runtr("Swahili: jani (sw) 5 or 6, msahafu (sw) 3 or 4")
        self.assertEqual(self.wxr.wtp.debugs, [])
        self.assertEqual(
            data,
            {
                "translations": [
                    {
                        "word": "jani",
                        "lang": "Swahili",
                        "code": "sw",  # DEPRECATED for "lang_code"
                        "lang_code": "sw",
                        "tags": ["class-5", "class-6"],
                    },
                    {
                        "word": "msahafu",
                        "lang": "Swahili",
                        "code": "sw",  # DEPRECATED for "lang_code"
                        "lang_code": "sw",
                        "tags": ["class-3", "class-4"],
                    },
                ]
            },
        )

    def test_tr21(self):
        data = self.runtr("Xhosa: igqabi 5 or 6")
        self.assertEqual(self.wxr.wtp.debugs, [])
        self.assertEqual(
            data,
            {
                "translations": [
                    {
                        "word": "igqabi",
                        "lang": "Xhosa",
                        "code": "xh",  # DEPRECATED for "lang_code"
                        "lang_code": "xh",
                        "tags": ["class-5", "class-6"],
                    },
                ]
            },
        )

    def test_tr22(self):
        data = self.runtr("Zulu: ikhasi (zu) 5 or 6, iqabi (zu) 5 or 6")
        self.assertEqual(self.wxr.wtp.debugs, [])
        self.assertEqual(
            data,
            {
                "translations": [
                    {
                        "word": "ikhasi",
                        "lang": "Zulu",
                        "code": "zu",  # DEPRECATED for "lang_code"
                        "lang_code": "zu",
                        "tags": ["class-5", "class-6"],
                    },
                    {
                        "word": "iqabi",
                        "lang": "Zulu",
                        "code": "zu",  # DEPRECATED for "lang_code"
                        "lang_code": "zu",
                        "tags": ["class-5", "class-6"],
                    },
                ]
            },
        )

    def test_tr23(self):
        data = self.runtr("Belarusian: ліст m (list)")
        self.assertEqual(self.wxr.wtp.debugs, [])
        self.assertEqual(
            data,
            {
                "translations": [
                    {
                        "word": "ліст",
                        "lang": "Belarusian",
                        "code": "be",  # DEPRECATED for "lang_code"
                        "lang_code": "be",
                        "roman": "list",
                        "tags": ["masculine"],
                    },
                ]
            },
        )

    def test_tr24(self):
        data = self.runtr("Puxian Min: foo", lang="Chinese")
        self.assertEqual(self.wxr.wtp.debugs, [])
        self.assertEqual(
            data,
            {
                "translations": [
                    {
                        "code": "zh",  # DEPRECATED for "lang_code"
                        "lang_code": "zh",
                        "lang": "Chinese",
                        "tags": ["Puxian-Min"],
                        "word": "foo",
                    }
                ],
            },
        )

    def test_tr25(self):
        data = self.runtr("Hallig and Mooring: foo", lang="Danish")
        self.assertEqual(self.wxr.wtp.debugs, [])
        # Special cases with Frisian, so test tr_second_tagmap handling
        # with bogus Danish instead...
        self.assertEqual(
            data,
            {
                "translations": [
                    {
                        "word": "foo",
                        "lang": "Danish",
                        "code": "da",  # DEPRECATED for "lang_code"
                        "lang_code": "da",
                        "tags": ["Hallig", "Mooring"],
                    }
                ]
            },
        )

    def test_tr26(self):
        data = self.runtr("  Ancient: foo", lang="Greek")
        self.assertEqual(self.wxr.wtp.debugs, [])
        self.assertEqual(
            data,
            {
                "translations": [
                    {
                        "word": "foo",
                        "lang": "Ancient Greek",
                        "code": "grc",  # DEPRECATED for "lang_code"
                        "lang_code": "grc",
                    }
                ]
            },
        )

    def test_tr27(self):
        data = self.runtr(
            "  Proto-Germanic: *foo",
            lang="Proto-Germanic",
            is_reconstruction=True,
        )
        self.assertEqual(self.wxr.wtp.debugs, [])
        self.assertEqual(
            data,
            {
                "translations": [
                    {
                        "word": "foo",
                        "lang": "Proto-Germanic",
                        "code": "gem-pro",  # DEPRECATED for "lang_code"
                        "lang_code": "gem-pro",
                    }
                ]
            },
        )

    # XXX for now this kind of or splitting is broken
    # def test_tr7(self):
    #     data = self.runtr("Swedish: foo f or bar m")
    #     self.assertEqual(data, {"translations": [
    #         {"word": "foo", "lang": "Swedish", "code": "sv", "lang_code": "sv",
    #          "tags": ["feminine"]},
    #         {"word": "bar", "lang": "Swedish", "code": "sv", "lang_code": "sv",
    #          "tags": ["masculine"]},
    #         ]})
