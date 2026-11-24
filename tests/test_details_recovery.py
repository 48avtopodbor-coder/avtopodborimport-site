import contextlib
import importlib.util
from pathlib import Path
import sqlite3
import sys
import types
import unittest
from unittest.mock import Mock, patch


class DetailsRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.db.row_factory = sqlite3.Row
        self.db.execute('CREATE TABLE specs (spec_id TEXT PRIMARY KEY, fuel TEXT, drive TEXT, gearbox TEXT, power_hp INTEGER, engine_ml INTEGER, tires TEXT, params_text TEXT, params_json TEXT, full INTEGER, fetched_at TEXT)')
        self.api = types.SimpleNamespace(car_params=Mock())
        database = types.SimpleNamespace(init_db=lambda: None, get_conn=lambda: contextlib.nullcontext(self.db))
        modules = {'che168_api': self.api, 'database': database,
                   'loguru': types.SimpleNamespace(logger=Mock())}
        path = Path(__file__).parents[1] / 'scripts/collector/details.py'
        spec = importlib.util.spec_from_file_location('collector_details_under_test', path)
        self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, modules):
            spec.loader.exec_module(self.module)

    def tearDown(self):
        self.db.close()

    def test_registration_only_response_does_not_poison_shared_spec(self):
        self.api.car_params.return_value = [('牌照信息', [('首次上牌时间', '2022-03-01')])]
        self.module.spec_info('42', '100')
        self.assertEqual(self.db.execute('SELECT count(*) FROM specs').fetchone()[0], 0)

    def test_old_incomplete_cache_is_refetched_and_repaired(self):
        self.db.execute("INSERT INTO specs (spec_id,full) VALUES ('42',1)")
        self.api.car_params.return_value = [('基本参数', [('能源类型', '汽油'), ('驱动方式', '前驱'), ('最大马力(Ps)', '150')])]
        result = self.module.spec_info('42', '100')
        self.api.car_params.assert_called_once_with('100')
        self.assertEqual((result['fuel'], result['drive'], result['power_hp']), ('бензин', 'передний', 150))
        self.assertEqual(self.db.execute("SELECT full FROM specs WHERE spec_id='42'").fetchone()[0], 1)

    def test_complete_cache_avoids_duplicate_api_request(self):
        self.db.execute("INSERT INTO specs (spec_id,full,fuel,drive,power_hp) VALUES ('42',1,'электро','полный',400)")
        self.assertEqual(self.module.spec_info('42', '100')['power_hp'], 400)
        self.api.car_params.assert_not_called()

    def test_engine_volume_uses_explicit_units_and_prefers_precise_ml(self):
        self.assertEqual(self.module.engine_ml({'排量(L)': '1.5'}), 1500)
        self.assertEqual(self.module.engine_ml({'排量(mL)': '1497', '排量(L)': '1.5'}), 1497)
        self.assertIsNone(self.module.engine_ml({'排量(L)': '-'}))
        self.assertIsNone(self.module.engine_ml({'发动机': '1.5T 150马力 L4'}))

    def test_retry_only_old_incomplete_active_records(self):
        self.db.execute('CREATE TABLE cars (listing_id TEXT,is_active INTEGER,params_at TEXT,photos TEXT,fuel TEXT,drive TEXT,power_hp INTEGER)')
        rows = [('old',1,'2000-01-01','[]',None,None,None),
                ('recent',1,'2999-01-01','[]',None,None,None),
                ('complete',1,'2000-01-01','[]','электро','полный',400),
                ('sold',0,'2000-01-01','[]',None,None,None),
                ('new',1,None,None,None,None,None)]
        self.db.executemany('INSERT INTO cars VALUES (?,?,?,?,?,?,?)',rows)
        selected = {r[0] for r in self.db.execute('SELECT listing_id FROM cars WHERE '+self.module.PENDING_DETAILS_WHERE)}
        self.assertEqual(selected, {'old','new'})

    def test_saved_volume_backfill_preserves_values_and_is_repeatable(self):
        import io
        import json
        self.db.execute('CREATE TABLE cars (spec_id TEXT,is_active INTEGER,price_cny INTEGER,engine_ml INTEGER)')
        raw = json.dumps([['发动机', [['排量(L)', '1.5']]]])
        self.db.executemany('INSERT INTO specs (spec_id,params_json,engine_ml) VALUES (?,?,?)', [('a',raw,None),('b',raw,1497)])
        self.db.executemany('INSERT INTO cars VALUES (?,?,?,?)', [('a',1,100,None),('b',1,100,1497)])
        path = Path(__file__).parents[1] / 'scripts/collector/backfill_engine_volumes.py'
        spec = importlib.util.spec_from_file_location('volume_backfill_under_test', path)
        module = importlib.util.module_from_spec(spec)
        database = types.SimpleNamespace(get_conn=lambda: contextlib.nullcontext(self.db))
        with patch.dict(sys.modules, {'details': self.module, 'database': database}):
            spec.loader.exec_module(module)
        with patch.object(sys, 'argv', ['backfill']), contextlib.redirect_stdout(io.StringIO()):
            module.main()
        self.assertIsNone(self.db.execute("SELECT engine_ml FROM cars WHERE spec_id='a'").fetchone()[0])
        with patch.object(sys, 'argv', ['backfill','--apply']), contextlib.redirect_stdout(io.StringIO()):
            module.main()
            module.main()
        self.assertEqual([r[0] for r in self.db.execute('SELECT engine_ml FROM cars ORDER BY spec_id')], [1500,1497])


if __name__ == '__main__':
    unittest.main()
