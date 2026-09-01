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
            with patch.object(v21_demo, "credentials_configured", return_value=False), \
                    patch.object(v21_demo, "market_client_for", return_value=object()), \
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

    def test_auto_start_triggers_immediate_scan_and_600_second_schedule(self):
        state = v21_demo.initial_state()
        app = SimpleNamespace(state=SimpleNamespace(v21_demo=state, binance_demo={}, http=object()))
        request = SimpleNamespace(app=app)

        async def fake_scan(_client, _occupied, _settings):
            return [{
                "symbol": "BTCUSDT", "direction": "LONG", "opportunity_score": 95, "confidence": 89,
                "score": 95, "trend": "Güçlü yükseliş", "volume_ratio": 1.2, "rsi": 62, "momentum": "Pozitif",
                "risk_reward": 3.2, "status": "SELECTED", "entry": 64000.0, "stop_loss": 63680.0,
                "tp1": 64500.0, "tp2": 65000.0, "tp3": 65500.0, "mtf_trend": "UYUMLU LONG",
                "macd_confirmation": True,
            }]

        with patch.object(v21_demo, "client_for", return_value=object()), \
                patch.object(v21_demo, "armed", return_value=True), \
                patch.object(v21_demo, "credentials_configured", return_value=True), \
                patch.object(v21_demo, "account_snapshot", new=AsyncMock(return_value={"positions": [], "open_orders": []})), \
                patch.object(v21_demo, "market_client_for", return_value=object()), \
                patch.object(v21_demo, "scan_demo_universe", new=fake_scan), \
                patch.object(v21_demo, "execute_demo_order", new=AsyncMock(return_value={"plan": {"entry_price": 64000.0, "margin_usdt": 50.0, "leverage": 2, "targets": [64500.0, 65000.0, 65500.0], "stop_loss": 63680.0, "status": "AÇIK"}})), \
                patch.object(v21_demo, "persist_state"):
            asyncio.run(v21_demo.v21_auto_start(request, v21_demo.AutoStartRequest(confirmation="DEMO OTOMATİK")))

        self.assertTrue(state["auto"]["enabled"])
        self.assertIsNotNone(state["scanner"]["last_scan_at"])
        self.assertIsNotNone(state["scanner"]["next_scan_at"])
        completion = __import__("datetime").datetime.fromisoformat(state["scanner"]["last_scan_at"].replace("Z", "+00:00"))
        next_scan = __import__("datetime").datetime.fromisoformat(state["scanner"]["next_scan_at"].replace("Z", "+00:00"))
        self.assertEqual(int((next_scan - completion).total_seconds()), 600)

    def test_scan_candidate_state_updates_when_new_response_arrives(self):
        state = v21_demo.initial_state()
        app = SimpleNamespace(state=SimpleNamespace(v21_demo=state, http=object()))
        payload = [{
            "symbol": "SOLUSDT", "direction": "LONG", "score": 91, "opportunity_score": 91, "confidence": 83,
            "trend": "Yükseliş", "volume_ratio": 1.35, "rsi": 58, "momentum": "Pozitif",
            "risk_reward": 2.7, "status": "SELECTED", "entry": 160.0, "stop_loss": 156.0,
            "tp1": 164.0, "tp2": 168.0, "tp3": 172.0, "mtf_trend": "UYUMLU LONG",
            "macd_confirmation": True,
        }]
        with patch.object(v21_demo, "credentials_configured", return_value=False), \
                patch.object(v21_demo, "market_client_for", return_value=object()), \
                patch.object(v21_demo, "account_snapshot", new=AsyncMock(return_value={"positions": [], "open_orders": []})), \
                patch.object(v21_demo, "scan_demo_universe", new=AsyncMock(return_value=payload)), \
                patch.object(v21_demo, "persist_state"):
            asyncio.run(v21_demo.run_scanner_cycle(app))
        self.assertEqual(state["scanner"]["top_candidates"][0]["symbol"], "SOLUSDT")
        self.assertEqual(state["scanner"]["selected_symbols"][0], "SOLUSDT")


if __name__ == "__main__":
    unittest.main(verbosity=2)
