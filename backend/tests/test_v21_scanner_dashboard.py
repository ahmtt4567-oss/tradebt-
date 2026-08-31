import asyncio
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

BACKEND = Path(__file__).parents[1]
sys.path.insert(0, str(BACKEND))

from app import v21_demo  # noqa: E402


class V21ScannerDashboardTests(unittest.TestCase):
    def test_scanner_interval_and_candidate_score_contract(self):
        self.assertEqual(v21_demo.SCAN_INTERVAL_SECONDS, 600)
        candidates = v21_demo._enrich_scan_candidates([
            {"symbol": "LOWUSDT", "direction": "BEKLE", "opportunity_score": -10, "confidence": 20},
            {"symbol": "TOPUSDT", "direction": "LONG", "opportunity_score": 130, "confidence": 88,
             "trend": "Güçlü yükseliş", "mtf_trend": "UYUMLU LONG", "volume_ratio": 1.4,
             "rsi": 61, "macd_confirmation": True, "momentum": "Pozitif", "risk_reward": 3},
        ])
        self.assertEqual([item["symbol"] for item in candidates], ["TOPUSDT", "LOWUSDT"])
        self.assertEqual(candidates[0]["score"], 100)
        self.assertIn("MACD confirmation", candidates[0]["reasons"])
        self.assertIn("1h/4h trend: UYUMLU LONG", candidates[0]["reasons"])
        self.assertIn("Volume ortalamanın üzerinde", candidates[0]["reasons"])
        self.assertTrue(candidates[0]["macd_confirmation"])

    def test_summary_exposes_scanner_and_automation_history(self):
        state = v21_demo.initial_state()
        state["scanner"]["selected_symbols"] = ["BTCUSDT"]
        state["scanner"]["scan_duration_ms"] = 1250
        state["automation_trades"] = [{"symbol": "BTCUSDT", "scanner_rank": 1}]
        payload = v21_demo.summary_payload(state)
        self.assertEqual(payload["scanner"]["scan_interval_seconds"], 600)
        self.assertEqual(payload["scanner"]["selected_count"], 1)
        self.assertEqual(payload["scanner"]["scan_duration_seconds"], 1.25)
        self.assertEqual(payload["automation_trades"][0]["scanner_rank"], 1)

    def test_concurrent_manual_scans_are_serialized(self):
        state = v21_demo.initial_state()
        app = SimpleNamespace(state=SimpleNamespace(v21_demo=state))
        started = asyncio.Event()
        release = asyncio.Event()
        scan_calls = 0

        async def scan(_client, _occupied, _settings):
            nonlocal scan_calls
            scan_calls += 1
            started.set()
            await release.wait()
            return [{"symbol": "BTCUSDT", "direction": "LONG", "opportunity_score": 90, "confidence": 90,
                     "trend": "Güçlü yükseliş", "volume_ratio": 1.2, "rsi": 60, "momentum": "Pozitif",
                     "risk_reward": 3, "status": "SELECTED"}]

        async def exercise():
            with patch.object(v21_demo, "credentials_configured", return_value=True), \
                    patch.object(v21_demo, "client_for", return_value=object()), \
                    patch.object(v21_demo, "account_snapshot", new=AsyncMock(return_value={"positions": [], "open_orders": []})), \
                    patch.object(v21_demo, "scan_demo_universe", new=scan) as scanner, \
                    patch.object(v21_demo, "persist_state"):
                first = asyncio.create_task(v21_demo.run_scanner_cycle(app))
                await started.wait()
                second = asyncio.create_task(v21_demo.run_scanner_cycle(app))
                await asyncio.sleep(0)
                release.set()
                await asyncio.gather(first, second)
                return scan_calls

            scan_call_count = asyncio.run(exercise())
            self.assertEqual(scan_call_count, 1)

    def test_scanner_does_not_start_trade_when_auto_is_disabled(self):
        state = v21_demo.initial_state()
        app = SimpleNamespace(state=SimpleNamespace(v21_demo=state))
        with patch.object(v21_demo, "execute_demo_order", new=AsyncMock()) as order:
            asyncio.run(v21_demo.automatic_cycle(app))
        order.assert_not_awaited()
        self.assertIn("onayıyla", state["auto"]["last_decision"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
