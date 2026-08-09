import ast
import unittest
from pathlib import Path


SOURCE_PATH = Path(__file__).parents[1] / "app" / "main.py"
SOURCE_TEXT = SOURCE_PATH.read_text(encoding="utf-8")
FRONTEND_TEXT = (Path(__file__).parents[2] / "frontend" / "src" / "App.tsx").read_text(encoding="utf-8")
STYLE_TEXT = (Path(__file__).parents[2] / "frontend" / "src" / "v12.css").read_text(encoding="utf-8")
TREE = ast.parse(SOURCE_TEXT)


def load_functions(*names):
    nodes = [node for node in TREE.body if isinstance(node, ast.FunctionDef) and node.name in names]
    namespace = {}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(SOURCE_PATH), "exec"), namespace)
    return namespace


CORE = load_functions(
    "paper_bot_policy",
    "paper_training_liquidity_allowed",
    "v20_target_plan",
    "demo_paper_trade_plan",
    "paper_performance_payload",
)


class V12PaperPilotTests(unittest.TestCase):
    def test_training_policy_is_faster_but_keeps_both_order_channels_locked(self):
        training = CORE["paper_bot_policy"](True)
        strict = CORE["paper_bot_policy"](False)
        self.assertLess(training["cycle_seconds"], strict["cycle_seconds"])
        self.assertLess(training["minimum_confidence"], strict["minimum_confidence"])
        self.assertGreater(training["maximum_trap_score"], strict["maximum_trap_score"])
        for policy in (training, strict):
            self.assertFalse(policy["orders_enabled"])
            self.assertFalse(policy["testnet_orders_enabled"])

    def test_training_liquidity_relaxation_only_accepts_bounded_one_sided_book(self):
        safe_training_book = {
            "auto_allowed": False,
            "mode": "TEK YÖNLÜ DEFTER",
            "spread_bps": 6.0,
            "depth_usdt": 55_000.0,
            "liquidity_score": 62,
        }
        self.assertTrue(CORE["paper_training_liquidity_allowed"](safe_training_book, True))
        self.assertFalse(CORE["paper_training_liquidity_allowed"](safe_training_book, False))
        self.assertFalse(CORE["paper_training_liquidity_allowed"]({**safe_training_book, "depth_usdt": 2_000.0}, True))
        self.assertTrue(CORE["paper_training_liquidity_allowed"]({"auto_allowed": True}, False))

    def test_demo_plan_builds_valid_long_and_short_levels_from_live_price(self):
        long_plan = CORE["demo_paper_trade_plan"]({"direction": "LONG", "atr": 2.0}, 100.0)
        short_plan = CORE["demo_paper_trade_plan"]({"direction": "SHORT", "atr": 2.0}, 100.0)
        self.assertLess(long_plan["stop_loss"], 100.0)
        self.assertGreater(long_plan["take_profit"], 100.0)
        self.assertGreater(short_plan["stop_loss"], 100.0)
        self.assertLess(short_plan["take_profit"], 100.0)
        self.assertEqual(long_plan["amount"], 50.0)
        self.assertFalse(long_plan["orders_enabled"])
        self.assertFalse(short_plan["testnet_orders_enabled"])

    def test_wait_signal_uses_visible_ema_direction_for_training_plan(self):
        long_plan = CORE["demo_paper_trade_plan"]({"direction": "BEKLE", "ema": {"ema20": 102, "ema50": 100}}, 101.0)
        short_plan = CORE["demo_paper_trade_plan"]({"direction": "BEKLE", "ema": {"ema20": 98, "ema50": 100}}, 99.0)
        self.assertEqual(long_plan["direction"], "LONG")
        self.assertEqual(short_plan["direction"], "SHORT")

    def test_performance_keeps_demo_auto_and_manual_results_separate(self):
        payload = CORE["paper_performance_payload"]({"trades": [
            {"source": "DEMO", "realized_pnl": 1.2},
            {"source": "AUTO", "realized_pnl": -0.4},
            {"source": "MANUAL", "realized_pnl": 0.6},
        ]})
        self.assertEqual(payload["demo_trades"], 1)
        self.assertEqual(payload["auto_trades"], 1)
        self.assertEqual(payload["manual_trades"], 1)

    def test_v12_exposes_demo_controls_and_contains_no_exchange_order_call(self):
        lowered = SOURCE_TEXT.lower()
        self.assertIn('/api/paper/demo/{symbol}', SOURCE_TEXT)
        self.assertIn('/api/paper/bot/training/toggle', SOURCE_TEXT)
        self.assertIn('version="20.2.0"', SOURCE_TEXT)
        self.assertIn('ŞİMDİ 50 USDT DEMO AÇ', FRONTEND_TEXT)
        self.assertIn('.paperPilotRibbon', STYLE_TEXT)
        self.assertNotIn('/api/v3/order', lowered)
        self.assertNotIn('fapi/v1/order', lowered)
        self.assertNotIn('create_order(', lowered)
        self.assertNotIn('place_order(', lowered)


if __name__ == "__main__":
    unittest.main(verbosity=2)
