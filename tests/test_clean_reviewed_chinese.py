import importlib.util
from pathlib import Path
import unittest


script = Path(__file__).resolve().parents[1] / "scripts/clean_reviewed_chinese.py"
spec = importlib.util.spec_from_file_location("clean_reviewed_chinese", script)
cleaner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cleaner)


class ChineseCleanupTests(unittest.TestCase):
    def test_latest_clean_version_is_not_selected_again(self):
        rows = [
            {"text": "查博士", "ru": "Ча Боши (查博士)", "qa_checked": True},
            {"text": "查博士", "ru": "Ча Боши", "qa_checked": True},
            {"text": "原漆", "ru": "Заводская окраска (原漆)", "qa_checked": True},
        ]
        batch, pending = cleaner.select_batch(rows, 40, 40000)
        self.assertEqual(pending, 1)
        self.assertEqual([row["text"] for row in batch], ["原漆"])

    def test_chinese_remnant_is_rejected(self):
        batch = [{"id": 1, "text": "查博士", "ru": "Ча Боши (查博士)", "qa_checked": True}]
        with self.assertRaises(ValueError):
            cleaner.validate(batch, {"translations": [{"id": 1, "ru": "Ча Боши (查博士)"}]})
        result, rejected = cleaner.validate(batch, {"translations": [{"id": 1, "ru": "Ча Боши"}]})
        self.assertEqual(rejected, [])
        self.assertFalse(result[0]["qa_unresolved_cjk"])
        self.assertTrue(result[0]["cjk_cleaned"])

    def test_valid_corrections_survive_one_invalid_correction(self):
        batch = [
            {"id": 1, "text": "原漆", "ru": "Заводская окраска (原漆)", "qa_checked": True},
            {"id": 2, "text": "查博士", "ru": "Ча Боши (查博士)", "qa_checked": True},
        ]
        result, rejected = cleaner.validate(batch, {"translations": [
            {"id": 1, "ru": "Заводская окраска"},
            {"id": 2, "ru": "Ча Боши (查博士)"},
        ]})
        self.assertEqual([row["text"] for row in result], ["原漆"])
        self.assertEqual(rejected, [2])


if __name__ == "__main__":
    unittest.main()
