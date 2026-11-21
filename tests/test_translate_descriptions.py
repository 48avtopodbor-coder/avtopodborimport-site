import importlib.util
import json
from pathlib import Path
import unittest


root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "translate_descriptions", root / "scripts" / "translate_seller_descriptions.py"
)
worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)


class DictionaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dictionary, cls.revision = worker.load_dictionary(root / "src" / "lib" / "seller-dictionary.json")

    def test_uncertain_mileage_is_preserved(self):
        status, text = worker.translate("原漆，不保实表", self.dictionary)
        self.assertEqual(status, "dictionary")
        self.assertIn("пробега продавец не гарантирует", text)

    def test_unrecognized_warning_is_not_dropped(self):
        status, text = worker.translate("原漆，无事故，发动机损坏", self.dictionary)
        self.assertEqual((status, text), ("untranslated", None))

    def test_original_and_recognized_phrases(self):
        self.assertEqual(worker.translate("Русский текст", self.dictionary), ("original", None))
        status, text = worker.translate("原漆，无事故，无火烧", self.dictionary)
        self.assertEqual(status, "dictionary")
        self.assertIn("ДТП", text)
        self.assertIn("пожара нет", text)

    def test_new_short_description(self):
        status, text = worker.translate("全车原版原漆，保实表", self.dictionary)
        self.assertEqual(status, "dictionary")
        self.assertIn("достоверность пробега", text)

    def test_accident_disclosure_is_not_hidden(self):
        status, text = worker.translate("此车为事故车，低于市场价销售", self.dictionary)
        self.assertEqual(status, "dictionary")
        self.assertIn("был в ДТП", text)

    def test_unrecognized_dealer_conditions_are_not_truncated(self):
        status, text = worker.translate("原版原漆，售后条款另议", self.dictionary)
        self.assertEqual((status, text), ("untranslated", None))

    def test_manual_translation_preserves_export_refusal(self):
        status, text = worker.translate("同行不批，出口勿扰。", self.dictionary)
        self.assertEqual(status, "dictionary")
        self.assertIn("экспорта не обращаться", text)

    def test_manual_translation_preserves_average_condition(self):
        source, translated = next(
            (source, translated)
            for source, translated in self.dictionary["descriptions"].items()
            if "整体车况一般" in source and "车身没有喷漆痕迹" in source
        )
        self.assertIn("среднее", translated)
        self.assertIn("следов перекраски нет", translated)

    def test_manual_translation_discloses_bodywork(self):
        status, text = worker.translate(
            "车子有油漆面和钣金，淡季洗货台台都是批发价亏本价，欢迎客户到店看车。",
            self.dictionary,
        )
        self.assertEqual(status, "dictionary")
        self.assertIn("кузовные работы", text)

    def test_manual_translation_preserves_export_refusal_and_down_payment(self):
        source, translated = next(
            (source, translated)
            for source, translated in self.dictionary["descriptions"].items()
            if source.startswith("出口，同行没有合作")
        )
        self.assertIn("не сотрудничает с экспортёрами", translated)
        self.assertIn("от 10%", translated)

    def test_revision_changes_with_dictionary(self):
        canonical = json.dumps(self.dictionary, ensure_ascii=False, separators=(",", ":"))
        import hashlib

        self.assertEqual(self.revision, hashlib.sha256(canonical.encode("utf-8")).hexdigest())


if __name__ == "__main__":
    unittest.main()
