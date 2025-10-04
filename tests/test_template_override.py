import unittest

from wikitextprocessor import Wtp

from wiktextract.template_override import template_override_fns


class TemplateOverrideTests(unittest.TestCase):
    def setUp(self) -> None:
        self.wtp = Wtp(lang_code="en", template_override_funcs=template_override_fns)
        self.wtp.start_page("TemplateOverride")

    def tearDown(self) -> None:
        self.wtp.close_db_conn()

    def test_section_link_two_params(self) -> None:
        result = self.wtp.expand(
            "{{section link|Wiktionary:Entry layout|Translations}}"
        )
        self.assertEqual(
            result,
            "[[Wiktionary:Entry layout#Translations|Translations]]",
        )

    def test_section_link_single_param_with_anchor(self) -> None:
        result = self.wtp.expand(
            "{{section link|Wiktionary:Entry layout#Translations}}"
        )
        self.assertEqual(
            result,
            "[[Wiktionary:Entry layout#Translations|Translations]]",
        )

    def test_section_link_named_parameters(self) -> None:
        result = self.wtp.expand(
            "{{section link|page=Wiktionary:Entry layout|section=Translations|display=Read more}}"
        )
        self.assertEqual(
            result,
            "[[Wiktionary:Entry layout#Translations|Read more]]",
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
