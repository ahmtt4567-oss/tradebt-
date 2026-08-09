import ast
import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


SOURCE_PATH = Path(__file__).parents[1] / "app" / "main.py"
SOURCE_TEXT = SOURCE_PATH.read_text(encoding="utf-8")
TREE = ast.parse(SOURCE_TEXT)


def load_functions(*names):
    nodes = [node for node in TREE.body if isinstance(node, ast.FunctionDef) and node.name in names]
    namespace = {
        "datetime": datetime,
        "timedelta": timedelta,
        "timezone": timezone,
        "json": json,
        "time": __import__("time"),
        "V9_DEFAULT_UNIVERSE": ("BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"),
        "V9_STREAM_STALE_SECONDS": 8,
        "V9_EVENT_LIMIT": 100,
        "V9_FILL_LIMIT": 160,
    }
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(SOURCE_PATH), "exec"), namespace)
    return namespace


CORE = load_functions(
    "safe_json_object",
    "empty_v9_market_twin_state",
    "v9_detect_gap",
    "v9_paper_fill_model",
    "v9_strategy_drift",
    "v9_pnl_attribution",
    "v9_daily_report_payload",
    "v9_market_twin_payload",
)


class V9LogicTests(unittest.TestCase):
    def test_legacy_event_details_never_crash_startup_restore(self):
        self.assertEqual(CORE["safe_json_object"]('{"source":"legacy"}'), {"source": "legacy"})
        self.assertEqual(CORE["safe_json_object"]("x"), {})
        self.assertEqual(CORE["safe_json_object"](["broken"]), {})

    def test_restart_state_requires_manual_approval_and_locks_orders(self):
        state = CORE["empty_v9_market_twin_state"]()
        self.assertFalse(state["enabled"])
        self.assertEqual(state["stream_health"], "BEKLEMEDE")
        self.assertFalse(state["orders_enabled"])
        self.assertFalse(state["testnet_orders_enabled"])

    def test_gap_detector_only_flags_material_stream_breaks(self):
        now = datetime.now(timezone.utc)
        healthy = CORE["v9_detect_gap"](now - timedelta(seconds=2), now)
        broken = CORE["v9_detect_gap"](now - timedelta(seconds=14), now)
        self.assertFalse(healthy["detected"])
        self.assertTrue(broken["detected"])
        self.assertGreater(broken["missing_windows"], 0)

    def test_paper_fill_models_partial_depth_costs_without_orders(self):
        book = {"bid": 99.9, "ask": 100.0, "bid_qty": 0.4, "ask_qty": 0.5, "spread_bps": 10.0}
        fill = CORE["v9_paper_fill_model"]("BUY", 100.0, book)
        self.assertAlmostEqual(fill["fill_pct"], 50.0, places=1)
        self.assertGreater(fill["execution_price"], book["ask"])
        self.assertGreater(fill["fee_usdt"], 0)
        self.assertFalse(fill["orders_enabled"])
        self.assertTrue(fill["paper_only"])

    def test_drift_radar_triggers_safe_rollback_on_sharp_degradation(self):
        recent_losses = [{"amount": 100, "realized_pnl": -3, "source": "AUTO"} for _ in range(10)]
        baseline_wins = [{"amount": 100, "realized_pnl": 2, "source": "AUTO"} for _ in range(10)]
        drift = CORE["v9_strategy_drift"](recent_losses + baseline_wins)
        self.assertEqual(drift["status"], "KRİTİK SAPMA")
        self.assertTrue(drift["rollback_required"])
        self.assertGreaterEqual(drift["drift_score"], 70)
        self.assertFalse(drift["orders_enabled"])

    def test_pnl_attribution_separates_realized_and_twin_mark_to_market(self):
        trades = [{"amount": 100, "realized_pnl": 5, "fee": 0.1, "source": "AUTO"}]
        fills = [{"symbol": "BTCUSDT", "side": "BUY", "strategy": "TREND", "execution_price": 100, "quantity": 1, "fee_usdt": 0.1}]
        attribution = CORE["v9_pnl_attribution"](trades, fills, {"BTCUSDT": {"price": 102}})
        self.assertEqual(len(attribution["items"]), 2)
        self.assertAlmostEqual(attribution["total_realized_pnl"], 5.0)
        self.assertAlmostEqual(attribution["total_unrealized_pnl"], 1.9)
        self.assertFalse(attribution["orders_enabled"])

    def test_dashboard_reports_live_coverage_and_paper_only_safety(self):
        state = CORE["empty_v9_market_twin_state"]()
        state["enabled"] = True
        state["stream_health"] = "BAĞLI"
        state["status"] = "CANLI KAYIT"
        now = datetime.now(timezone.utc).isoformat()
        state["latest"] = {
            symbol: {"time": now, "price": 100.0, "bid": 99.9, "ask": 100.1, "spread_bps": 20.0, "quote_volume_24h": 1_000_000}
            for symbol in state["universe"]
        }
        payload = CORE["v9_market_twin_payload"](state, [], "KALICI")
        self.assertEqual(payload["coverage_pct"], 100.0)
        self.assertEqual(payload["daily_report"]["status"], "CANLI VE SAĞLIKLI")
        self.assertFalse(payload["orders_enabled"])
        self.assertFalse(payload["testnet_orders_enabled"])

    def test_source_has_v9_endpoints_and_no_exchange_order_call(self):
        lowered = SOURCE_TEXT.lower()
        self.assertIn('/api/v9/twin', SOURCE_TEXT)
        self.assertIn('/api/v9/paper/order', SOURCE_TEXT)
        self.assertIn('version="20.2.0"', SOURCE_TEXT)
        self.assertNotIn('/api/v3/order', lowered)
        self.assertNotIn('fapi/v1/order', lowered)
        self.assertNotIn('create_order(', lowered)


if __name__ == "__main__":
    unittest.main(verbosity=2)
