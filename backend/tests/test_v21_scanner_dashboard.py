import asyncio
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

BACKEND = Path(__file__).parents[1]
sys.path.insert(0, str(BACKEND))

from app import v21_demo  # noqa: E402


ROOT_FRONTEND = Path(__file__).parents[2] / "BinanceDemo.tsx"


class V21ScannerDashboardTests(unittest.TestCase):
    def test_root_frontend_arm_uses_user_confirmation(self):
        source = ROOT_FRONTEND.read_text(encoding="utf-8")
        self.assertIn("confirmation:armText", source)
        self.assertNotIn("confirmation:'DEMO'", source)

    def test_performance_aggregation_uses_real_closed_journal_events(self):
        state = v21_demo.initial_state()
        state["journal"] = [
            {"kind": "POSITION_CLOSED", "created_at": "2026-09-01T10:00:00+00:00", "realized_pnl": 12.0},
            {"kind": "FILL", "reduce_only": True, "created_at": "2026-08-30T10:00:00+00:00", "realized_pnl": -4.0},
            {"kind": "AUTO_ORDER", "created_at": "2026-09-01T10:01:00+00:00", "realized_pnl": 999.0},
        ]
        result = v21_demo.performance_payload(state, "all")
        self.assertEqual(result["total_trades"], 2)
        self.assertEqual(result["total_profit"], 12.0)
        self.assertEqual(result["total_loss"], -4.0)
        self.assertEqual(result["net_profit"], 8.0)
        self.assertEqual(result["wins"], 1)
        self.assertEqual(result["losses"], 1)
        self.assertEqual(result["profit_factor"], 3.0)

    def _automation_app(self, candidate):
        state = v21_demo.initial_state()
        state["auto"].update({"enabled": True, "user_confirmed": True})
        state["settings"]["allowed_symbols"] = ["BTCUSDT"]
        app = SimpleNamespace(state=SimpleNamespace(v21_demo=state, binance_demo={}, http=object()))
        return state, app, candidate

    def test_automation_rejects_candidate_outside_allowed_symbols(self):
        candidate = {"symbol": "ETHUSDT", "direction": "LONG", "status": "SELECTED", "entry": 100.0,
                     "stop_loss": 99.0, "tp1": 101.0, "tp2": 102.0, "tp3": 103.0, "score": 95,
                     "opportunity_score": 95, "confidence": "HIGH", "reasons": []}
        state, app, candidate = self._automation_app(candidate)
        state["scanner"]["top_candidates"] = [candidate]
        with patch.object(v21_demo, "armed", return_value=True), \
                patch.object(v21_demo, "client_for", return_value=object()), \
                patch.object(v21_demo, "account_snapshot", new=AsyncMock(return_value={"positions": [], "open_orders": []})), \
                patch.object(v21_demo, "scan_demo_universe", new=AsyncMock(return_value=[candidate])), \
                patch.object(v21_demo, "execute_demo_order", new=AsyncMock()) as order, \
                patch.object(v21_demo, "persist_state"):
            asyncio.run(v21_demo.automatic_cycle(app))
        order.assert_not_awaited()
        self.assertEqual(state["auto"]["rejection_gate"], "ALLOWED_SYMBOLS")
        self.assertIn("ETHUSDT", state["auto"]["rejection_reason"])

    def test_automation_reaches_demo_execution_when_all_gates_pass(self):
        candidate = {"symbol": "BTCUSDT", "direction": "LONG", "status": "SELECTED", "entry": 100.0,
                     "stop_loss": 99.0, "tp1": 101.0, "tp2": 102.0, "tp3": 103.0, "score": 95,
                     "opportunity_score": 95, "confidence": "HIGH", "reasons": ["test"]}
        state, app, candidate = self._automation_app(candidate)
        result = {"plan": {"entry_price": 100.0, "targets": [101.0, 102.0, 103.0], "stop_loss": 99.0,
                            "margin_usdt": 5.0, "leverage": 2, "status": "AÇIK"}}
        with patch.object(v21_demo, "armed", return_value=True), \
                patch.object(v21_demo, "client_for", return_value=object()), \
                patch.object(v21_demo, "account_snapshot", new=AsyncMock(return_value={"positions": [], "open_orders": []})), \
                patch.object(v21_demo, "scan_demo_universe", new=AsyncMock(return_value=[candidate])), \
                patch.object(v21_demo, "execute_demo_order", new=AsyncMock(return_value=result)) as order, \
                patch.object(v21_demo, "persist_state"):
            asyncio.run(v21_demo.automatic_cycle(app))
        order.assert_awaited_once()
        self.assertEqual(order.await_args.kwargs["source"], "AUTO_SCANNER")
        self.assertEqual(state["auto"]["rejection_reason"], None)

    def test_demo_smoke_test_creates_local_paper_position_without_exchange_order(self):
        state = v21_demo.initial_state()
        state["auto"].update({"enabled": True, "user_confirmed": True})
        state["settings"]["allowed_symbols"] = ["BTCUSDT"]
        app = SimpleNamespace(state=SimpleNamespace(v21_demo=state, binance_demo={}, http=object()))
        request = SimpleNamespace(app=app)
        candidate = {"symbol": "BTCUSDT", "direction": "LONG", "status": "SELECTED", "entry": 100.0,
                     "stop_loss": 99.0, "tp1": 101.0, "tp2": 102.0, "tp3": 103.0, "score": 95,
                     "opportunity_score": 95, "confidence": "HIGH", "reasons": ["test"]}
        state["scanner"]["top_candidates"] = [candidate]
        with patch.object(v21_demo, "credentials_configured", return_value=False), \
                patch.object(v21_demo, "execute_demo_order", new=AsyncMock()) as order, \
                patch.object(v21_demo, "persist_state"):
            result = asyncio.run(v21_demo.v21_demo_smoke_test(request))
        order.assert_not_awaited()
        self.assertEqual(result["position"]["symbol"], "BTCUSDT")
        self.assertEqual(result["position"]["stop_loss"], 99.0)
        self.assertEqual(result["position"]["targets"], [101.0, 102.0, 103.0])
        self.assertEqual(len(state["paper_positions"]), 1)

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
        state["settings"]["scan_seconds"] = 30
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
        self.assertEqual((next_scan - completion).total_seconds(), 600)

    def test_scan_candidate_state_updates_when_new_response_arrives(self):
        state = v21_demo.initial_state()
        app = SimpleNamespace(state=SimpleNamespace(v21_demo=state, http=object()))
        first_payload = [{
            "symbol": "SOLUSDT", "direction": "LONG", "score": 91, "opportunity_score": 91, "confidence": 83,
            "trend": "Yükseliş", "volume_ratio": 1.35, "rsi": 58, "momentum": "Pozitif",
            "risk_reward": 2.7, "status": "SELECTED", "entry": 160.0, "stop_loss": 156.0,
            "tp1": 164.0, "tp2": 168.0, "tp3": 172.0, "mtf_trend": "UYUMLU LONG",
            "macd_confirmation": True,
        }]
        second_payload = [{
            "symbol": "ETHUSDT", "direction": "SHORT", "score": 88, "opportunity_score": 88, "confidence": 81,
            "trend": "Düşüş", "volume_ratio": 1.25, "rsi": 42, "momentum": "Negatif",
            "risk_reward": 2.4, "status": "SELECTED", "entry": 2450.0, "stop_loss": 2490.0,
            "tp1": 2410.0, "tp2": 2370.0, "tp3": 2330.0, "mtf_trend": "UYUMLU SHORT",
            "macd_confirmation": True,
        }]
        with patch.object(v21_demo, "credentials_configured", return_value=False), \
                patch.object(v21_demo, "market_client_for", return_value=object()), \
                patch.object(v21_demo, "account_snapshot", new=AsyncMock(return_value={"positions": [], "open_orders": []})), \
                patch.object(v21_demo, "scan_demo_universe", new=AsyncMock(side_effect=[first_payload, second_payload])), \
                patch.object(v21_demo, "persist_state"):
            asyncio.run(v21_demo.run_scanner_cycle(app))
            self.assertEqual(state["scanner"]["top_candidates"][0]["symbol"], "SOLUSDT")
            asyncio.run(v21_demo.run_scanner_cycle(app))
        self.assertEqual(state["scanner"]["top_candidates"][0]["symbol"], "ETHUSDT")
        self.assertEqual(state["scanner"]["selected_symbols"][0], "ETHUSDT")
        self.assertNotIn("SOLUSDT", state["scanner"]["selected_symbols"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
