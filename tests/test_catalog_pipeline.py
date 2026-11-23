from pathlib import Path
import sys
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
from car_titles import source_series, extract_title
from photo_relay import allowed, image_type
from translate_seller_descriptions import translate


class PipelineTests(unittest.TestCase):
    def test_partial_dictionary_does_not_publish_chinese(self):
        self.assertEqual(
            translate("测试", {"descriptions": {"测试": "Тест 中文"}, "phrases": {}}),
            ("untranslated", None),
        )
        self.assertEqual(
            translate("测试", {"descriptions": {}, "phrases": {"测试": "Тест 中文"}}),
            ("untranslated", None),
        )

    def test_url_allowlist(self):
        self.assertTrue(allowed("https://2sc2.autoimg.cn/a.jpg"))
        for u in (
            "http://2sc2.autoimg.cn/a",
            "https://autoimg.cn.evil.com/a",
            "https://evilautoimg.cn/a",
            "https://user@2sc2.autoimg.cn/a",
            "https://2sc2.autoimg.cn:22/a",
            "file:///etc/passwd",
        ):
            self.assertFalse(allowed(u), u)

    def test_images_not_html(self):
        self.assertIsNone(image_type(b"<html>blocked</html>"))
        self.assertEqual(image_type(b"\xff\xd8\xfftest"), "image/jpeg")

    def test_slash_titles(self):
        self.assertEqual(source_series("理想L9/1.5T/22款/Max", None), "理想L9")
        self.assertIsNone(source_series("unstructured / text", None))

    def test_shared_alias_preserves_original(self):
        original = "马自达3 昂克赛拉 2021款 2.0L 自动质雅版"
        result = extract_title(
            original, None, "马自达", {"马自达3 昂克赛拉": ("3", "3")}, "mazda"
        )
        self.assertEqual(result, ("3", "3", None))


if __name__ == "__main__":
    unittest.main()
