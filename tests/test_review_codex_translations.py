import importlib.util
from pathlib import Path
import unittest


script = Path(__file__).resolve().parents[1] / "scripts/review_codex_translations.py"
spec = importlib.util.spec_from_file_location("review_codex_translations", script)
reviewer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reviewer)


class ReviewTranslationTests(unittest.TestCase):
    def test_resume_skips_checked_text(self):
        rows = [{"text": "一手车", "ru": "Один владелец", "cars": 1},
                {"text": "原漆", "ru": "Заводская окраска", "cars": 2}]
        batch = reviewer.select_batch(rows, {"一手车"}, 80, 60000)
        self.assertEqual([row["text"] for row in batch], ["原漆"])

    def test_unknown_or_duplicate_corrections_fail(self):
        batch = [{"id": 1, "text": "一手车", "ru": "Один владелец", "cars": 1}]
        for identifier in (2, 1):
            items = [{"id": identifier, "ru": "Исправленный перевод", "reason": "Ошибка"}]
            if identifier == 1:
                items *= 2
            with self.assertRaises(ValueError):
                reviewer.apply_corrections(batch, {"corrections": items})

    def test_correction_keeps_original(self):
        batch = [{"id": 1, "text": "原漆", "ru": "Неверно", "cars": 2}]
        checked = reviewer.apply_corrections(batch, {"corrections": [
            {"id": 1, "ru": "Заводская окраска", "reason": "Уточнено"}]})
        self.assertEqual(checked[0]["text"], "原漆")
        self.assertEqual(checked[0]["ru"], "Заводская окраска")
        self.assertTrue(checked[0]["qa_checked"])
        self.assertFalse(checked[0]["qa_unresolved_cjk"])

    def test_parallel_partitions_are_disjoint_and_complete(self):
        rows = [{"text": f"Описание {i}", "ru": "Перевод", "cars": 1} for i in range(20)]
        first = reviewer.select_batch(rows, set(), 80, 60000, 0, 2)
        second = reviewer.select_batch(rows, set(), 80, 60000, 1, 2)
        self.assertFalse({r["text"] for r in first} & {r["text"] for r in second})
        self.assertEqual(len(first) + len(second), len(rows))


if __name__ == "__main__":
    unittest.main()
