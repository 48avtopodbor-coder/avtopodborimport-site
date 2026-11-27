import json
from pathlib import Path
import unittest

from scripts.seller_content import clean_seller_text, missing_numbers
from scripts.import_reviewed_seller_translations import prepare


class PublicContentTests(unittest.TestCase):
    def test_public_text(self):
        cases = json.loads(Path(__file__).with_name("seller-content-cases.json").read_text())
        for source, facts, removed in cases:
            with self.subTest(source=source):
                public = clean_seller_text(source)
                for fact in facts:
                    self.assertIn(fact, public)
                for item in removed:
                    self.assertNotIn(item, public)
                self.assertEqual(clean_seller_text(public), public)

    def test_wan_conversion_dates_and_contact_numbers(self):
        self.assertEqual(missing_numbers("2022年8月 8万公里，4.65万元", "08.2022, 80 тыс. км, 46 500 юаней"), [])
        self.assertEqual(missing_numbers("微信: dealer123，8万公里", "80 000 км"), [])
        self.assertEqual(missing_numbers("8万公里", "8 км"), ["80000"])
        self.assertEqual(missing_numbers("行驶8万，报价8万", "80 тыс. км"), ["80000"])

    def test_units_and_registration_context_stay_distinct(self):
        self.assertEqual(missing_numbers("续保10年，12.8 英寸，价格14.08", "10 лет, 12,8 дюйма, цена 14,08"), [])
        self.assertEqual(missing_numbers("23年宝马，3.5wkm，VK70 K系列", "BMW 2023 года, 35 000 км, серия VK70 K"), [])
        self.assertEqual(missing_numbers("上牌日期】22.6，3.3w，2.5?万公里，首付1到5成", "06.2022, 33 000, 25 тыс. км, взнос 10–50%"), [])

    def test_import_rechecks_final_text_and_lists_missing_numbers(self):
        original = "里程8万公里 微信: dealer123"
        clean = {"text": original, "ru": "Пробег 80 тыс. км. Telegram: @dealer123", "qa_checked": True}
        records, _ = prepare([clean])
        self.assertEqual(records[0][1], original)
        self.assertNotIn("dealer", records[0][2])
        manual = []
        records, rejected = prepare([clean, dict(clean, ru="Пробег 8 км")], manual)
        self.assertEqual(records, [])
        self.assertEqual(rejected["missing_numbers"], 1)
        self.assertEqual(manual[0]["missing_numbers"], ["80000"])
