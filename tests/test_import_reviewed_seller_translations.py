import hashlib
import importlib.util
from pathlib import Path
import unittest


script = Path(__file__).resolve().parents[1] / "scripts/import_reviewed_seller_translations.py"
spec = importlib.util.spec_from_file_location("import_reviewed_seller_translations", script)
importer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(importer)


class ReviewedImportTests(unittest.TestCase):
    def test_requires_qa_and_complete_russian_text(self):
        rows, rejected = importer.prepare([
            {"text": "原漆", "ru": "Заводская окраска", "qa_checked": True},
            {"text": "一手车", "ru": "Один владелец"},
            {"text": "查博士S", "ru": "Оценка 查博士 — S", "qa_checked": True},
        ])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], hashlib.md5("原漆".encode()).hexdigest())
        self.assertEqual(rejected["not_checked"], 1)
        self.assertEqual(rejected["chinese_remaining"], 1)

    def test_later_review_replaces_same_source_once(self):
        rows, rejected = importer.prepare([
            {"text": "原漆", "ru": "Заводская окраска", "qa_checked": True},
            {"text": "原漆", "ru": "Заводская краска", "qa_checked": True},
        ])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][2], "Заводская краска")
        self.assertEqual(sum(rejected.values()), 0)

    def test_latin_model_name_can_be_imported(self):
        rows, rejected = importer.prepare([
            {"text": "奔驰GLB", "ru": "Mercedes-Benz GLB.", "qa_checked": True},
        ])
        self.assertEqual(len(rows), 1)
        self.assertEqual(sum(rejected.values()), 0)


if __name__ == "__main__":
    unittest.main()
