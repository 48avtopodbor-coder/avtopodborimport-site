import unittest

from car_titles import extract_title, normalize_brand
from import_cars import CAR_COLS, enrich_car


class CarTitlesTest(unittest.TestCase):
    def test_brand_alias_normalization(self):
        self.assertEqual(normalize_brand(" Li-Auto "), "liauto")
        self.assertEqual(normalize_brand("ｌｉ　ａｕｔｏ"), "liauto")

    def test_known_jetta_title(self):
        title = extract_title(
            "捷达VS5 2022款 280TSI 自动进取型Pro", None, "捷达",
            {"捷达VS5": ("VS5", "vs5")}, "jetta",
        )
        self.assertEqual(title, ("VS5", "vs5", "280TSI Pro"))

    def test_unmapped_chinese_series_stays_empty(self):
        self.assertEqual(
            extract_title("未知车型 2022款 自动豪华型", None, None, {}, "unknown"),
            (None, None, None),
        )

    def test_latin_series_after_chinese_brand(self):
        self.assertEqual(
            extract_title("奥迪A6L 2021款 40 TFSI 豪华动感型", None, "奥迪", {}, "audi"),
            ("A6L", "a6l", None),
        )

    def test_import_marker_uses_same_model(self):
        self.assertEqual(
            extract_title("宝马5系(进口) 2022款 525i", None, "宝马", {
                "宝马5系": ("5 Series", "5-series")
            }, "bmw"),
            ("5 Series", "5-series", "525i"),
        )

    def test_unmapped_brand_is_preserved_for_reporting(self):
        row = [None] * len(CAR_COLS)
        row[CAR_COLS.index("brand_ru")] = "New Brand"
        row[CAR_COLS.index("model")] = "New Brand Z1 2022款"
        from collections import Counter
        unknown = Counter()
        enriched = enrich_car(row, {}, {}, unknown)
        self.assertEqual(enriched[-4:], (None, None, None, None))
        self.assertEqual(unknown["New Brand"], 1)


if __name__ == "__main__":
    unittest.main()
