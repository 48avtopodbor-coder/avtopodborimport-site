import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


COLLECTOR = Path(__file__).resolve().parents[1] / "scripts" / "collector"


class CollectorSoldStatusTests(unittest.TestCase):
    def test_sold_response_requires_an_explicit_indicator(self):
        with patch.object(sys, "path", [str(COLLECTOR), *sys.path]):
            from sold_status import is_sold_response

        for code, message, expected in (
            (99999, None, True),
            (1, "该车已下架", True),
            (404, "接口参数不存在", False),
            (1, "删除失败", False),
            (2, "查询已售车辆失败", False),
            (None, None, False),
        ):
            with self.subTest(code=code, message=message):
                self.assertEqual(is_sold_response(code, message), expected)

    def test_enrich_keeps_listing_on_failed_responses(self):
        module_spec = importlib.util.spec_from_file_location("enrich_under_test", COLLECTOR / "enrich.py")
        enrich = importlib.util.module_from_spec(module_spec)
        db = SimpleNamespace(init_db=Mock(), cars_to_enrich=Mock(), update_details=Mock(), get_conn=Mock())
        logger = Mock()
        with patch.object(sys, "path", [str(COLLECTOR), *sys.path]), patch.dict(
            sys.modules, {"database": db, "loguru": SimpleNamespace(logger=logger)}
        ):
            module_spec.loader.exec_module(enrich)
        messages = ["接口不存在", None, "删除失败", "查询已售车辆失败", "该车已下架"]
        with patch.object(enrich, "get_info", side_effect=[
            {"returncode": 2, "message": message} for message in messages
        ]), patch.object(enrich.time, "sleep"):
            counts = enrich.process(["1", "2", "3", "4", "5"], "Test")
        self.assertEqual(counts["fail"], 4)
        self.assertEqual(counts["sold"], 1)
        db.update_details.assert_called_once_with("5", {"is_active": 0})
        self.assertEqual([call.args[1:] for call in logger.warning.call_args_list], [
            ("1", 2, "接口不存在"), ("2", 2, None), ("3", 2, "删除失败"),
        ])
