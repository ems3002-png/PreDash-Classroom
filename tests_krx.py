import json
import sys
import types
import unittest
from datetime import date

try:
    import requests
except ImportError:
    requests = types.SimpleNamespace(RequestException=Exception)

from predash import krx


class FakeResponse:
    def __init__(self, rows, status=200):
        self._rows = rows
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.RequestException("HTTP error")

    def json(self):
        return {"OutBlock_1": self._rows}


class KRXDailyActivityTest(unittest.TestCase):
    def setUp(self):
        self.original_get = krx.requests.get

    def tearDown(self):
        krx.requests.get = self.original_get

    def test_current_isu_cd_matches(self):
        krx.requests.get = lambda *args, **kwargs: FakeResponse([
            {
                "BAS_DD": "20260930",
                "ISU_CD": "005930",
                "TDD_CLSPRC": "100000",
                "ACC_TRDVOL": "1,234",
                "ACC_TRDVAL": "12,345,678",
                "MKTCAP": "600,000,000",
            }
        ])
        result = krx.daily_activity("KEY", "005930", date(2026, 9, 30))
        self.assertEqual(result["date"], "2026-09-30")
        self.assertEqual(result["volume"], 1234)
        self.assertEqual(result["turnover"], 12345678)
        self.assertEqual(result["market_cap"], 600000000)
        self.assertEqual(result["market"], "코스피")

    def test_alternate_isu_srt_cd_is_supported(self):
        krx.requests.get = lambda *args, **kwargs: FakeResponse([
            {
                "BAS_DD": "20260930",
                "ISU_SRT_CD": "A005930",
                "ACC_TRDVOL": "10",
                "ACC_TRDVAL": "1000",
                "MKTCAP": "5000",
            }
        ])
        result = krx.daily_activity("KEY", "005930", date(2026, 9, 30))
        self.assertEqual(result["volume"], 10)

    def test_weekend_moves_back_to_friday(self):
        calls = []

        def fake_get(url, **kwargs):
            calls.append(kwargs["params"]["basDd"])
            if kwargs["params"]["basDd"] == "20260930":
                return FakeResponse([])
            return FakeResponse([
                {
                    "BAS_DD": "20260929",
                    "ISU_CD": "005930",
                    "ACC_TRDVOL": "10",
                    "ACC_TRDVAL": "1000",
                    "MKTCAP": "5000",
                }
            ])

        krx.requests.get = fake_get
        result = krx.daily_activity("KEY", "005930", date(2026, 9, 30))
        self.assertIsNotNone(result)
        self.assertEqual(result["date"], "2026-09-29")

    def test_bad_key_or_code_rejected(self):
        with self.assertRaises(krx.KRXError):
            krx.daily_activity("", "005930", date(2026, 9, 30))
        with self.assertRaises(krx.KRXError):
            krx.daily_activity("KEY", "123", date(2026, 9, 30))


if __name__ == "__main__":
    unittest.main()
