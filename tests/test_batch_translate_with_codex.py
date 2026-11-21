import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch


script = Path(__file__).resolve().parents[1] / "scripts/batch_translate_with_codex.py"
spec = importlib.util.spec_from_file_location("batch_translate_with_codex", script)
batcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(batcher)


class BatchTranslationTests(unittest.TestCase):
    def test_resume_and_normalized_duplicates(self):
        rows = [
            {"text": "原版原漆", "cars": 3},
            {"text": "原版 原漆", "cars": 2},
            {"text": "一手车", "cars": 4},
        ]
        batch, remaining = batcher.select_batch(rows, {"一手车"}, {}, 10, 100)
        self.assertEqual(remaining, 1)
        self.assertEqual([row["text"] for row in batch], ["原版原漆"])

    def test_missing_or_repeated_ids_fail_closed(self):
        batch = [{"id": 1, "text": "一手车", "cars": 1},
                 {"id": 2, "text": "原版原漆", "cars": 1}]
        with self.assertRaises(ValueError):
            batcher.validate(batch, {"translations": [{"id": 1, "ru": "Один владелец"}]})
        with self.assertRaises(ValueError):
            batcher.validate(batch, {"translations": [
                {"id": 1, "ru": "Один владелец"}, {"id": 1, "ru": "Повтор"}]})

    def test_numbers_and_chinese_are_marked_for_review(self):
        batch = [{"id": 1, "text": "2023年 5万公里", "cars": 1}]
        result = batcher.validate(batch, {"translations": [
            {"id": 1, "ru": "2023 год, пробег 50 000 км, 原漆"}]})
        self.assertEqual(len(result[0]["issues"]), 2)

    def test_latin_model_name_is_a_valid_translation(self):
        batch = [{"id": 1, "text": "奔驰GLB", "cars": 1}]
        result = batcher.validate(batch, {"translations": [
            {"id": 1, "ru": "Mercedes-Benz GLB."}]})
        self.assertEqual(result[0]["ru"], "Mercedes-Benz GLB.")

    def test_retry_only_missing_translation(self):
        batch = [{"id": 1, "text": "一手车", "cars": 1},
                 {"id": 2, "text": "原漆", "cars": 1}]
        answers = [
            {"translations": [{"id": 1, "ru": "Один владелец"}]},
            {"translations": [{"id": 2, "ru": "Заводская окраска"}]},
        ]
        with patch.object(batcher, "translate_batch", side_effect=answers) as model:
            result = batcher.translate_with_repair(batch, "codex", 10, Path("/tmp"))
        self.assertEqual(len(result), 2)
        self.assertEqual([row["id"] for row in model.call_args_list[1].args[0]], [2])

    def test_three_invalid_answers_stop_without_checkpoint(self):
        batch = [{"id": 1, "text": "原漆", "cars": 1}]
        with patch.object(batcher, "translate_batch", return_value={"translations": []}):
            with self.assertRaises(ValueError):
                batcher.translate_with_repair(batch, "codex", 10, Path("/tmp"))


if __name__ == "__main__":
    unittest.main()
