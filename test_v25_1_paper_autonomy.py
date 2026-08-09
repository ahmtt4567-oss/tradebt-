import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "app" / "paper_autonomy.py"
SPEC = importlib.util.spec_from_file_location("paper_autonomy", MODULE_PATH)
assert SPEC and SPEC.loader
AUTONOMY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUTONOMY)


class V251PaperAutonomyTests(unittest.TestCase):
    def test_profiles_expand_universe_and_exposure_in_bounded_steps(self):
        cautious = AUTONOMY.autonomy_policy("TEMKINLI")
        balanced = AUTONOMY.autonomy_policy("DENGELI")
        fast = AUTONOMY.autonomy_policy("HIZLI")
        self.assertLess(cautious["universe_size"], balanced["universe_size"])
        self.assertLess(balanced["universe_size"], fast["universe_size"])
        self.assertLess(cautious["max_allocation_pct"], balanced["max_allocation_pct"])
        self.assertLess(balanced["max_allocation_pct"], fast["max_allocation_pct"])
        for policy in (cautious, balanced, fast):
            self.assertTrue(policy["paper_only"])
            self.assertFalse(policy["orders_enabled"])
            self.assertFalse(policy["testnet_orders_enabled"])
            self.assertFalse(policy["profit_guaranteed"])
            self.assertLessEqual(policy["maximum_order_usdt"], 2_000)

    def test_candidate_ranking_prefers_eligible_quality(self):
        rows = [
            {"symbol": "AUSDT", "display": "A/USDT", "direction": "LONG", "confidence": 88, "trap_score": 20, "volume_ratio": 1.8, "change": 2.1, "price": 10, "volume": 1_000_000, "breakout": True},
            {"symbol": "BUSDT", "display": "B/USDT", "direction": "SHORT", "confidence": 76, "trap_score": 42, "volume_ratio": 1.2, "change": -1.0, "price": 20, "volume": 2_000_000, "breakout": False},
            {"symbol": "CUSDT", "display": "C/USDT", "direction": "LONG", "confidence": 95, "trap_score": 82, "volume_ratio": 3.0, "change": 8.0, "price": 30, "volume": 3_000_000, "breakout": True},
            {"symbol": "DUSDT", "display": "D/USDT", "direction": "BEKLE", "confidence": 99, "trap_score": 1, "volume_ratio": 3.0, "change": 9.0, "price": 40, "volume": 4_000_000, "breakout": False},
        ]
        ranked = AUTONOMY.rank_paper_candidates(rows, "DENGELI")
        self.assertEqual(ranked[0]["symbol"], "AUSDT")
        self.assertTrue(ranked[0]["eligible"])
        self.assertNotIn("DUSDT", {item["symbol"] for item in ranked})
        self.assertEqual([item["rank"] for item in ranked], list(range(1, len(ranked) + 1)))

    def test_balanced_allocation_is_visible_but_stays_inside_caps(self):
        allocation = AUTONOMY.dynamic_paper_allocation(
            balance=10_000,
            available=10_000,
            current_exposure=0,
            entry_price=100,
            stop_loss=99.75,
            tp3=100.75,
            confidence=86,
            risk_score=20,
            regime_multiplier=1.0,
            profile="DENGELI",
        )
        self.assertTrue(allocation["approved"])
        self.assertEqual(allocation["amount"], 1_500.0)
        self.assertGreaterEqual(allocation["projected_plan_net_usdt"], 5.0)
        self.assertLessEqual(allocation["allocation_pct"], 15.0)
        self.assertFalse(allocation["profit_guaranteed"])
        self.assertFalse(allocation["orders_enabled"])

    def test_allocation_respects_remaining_portfolio_exposure(self):
        allocation = AUTONOMY.dynamic_paper_allocation(
            balance=10_000,
            available=6_000,
            current_exposure=4_400,
            entry_price=100,
            stop_loss=99,
            tp3=103,
            confidence=90,
            risk_score=10,
            profile="DENGELI",
        )
        self.assertLessEqual(allocation["amount"], 100.0)
        self.assertFalse(allocation["approved"])
        self.assertEqual(allocation["status"], "NET FIRSAT YETERSİZ")

    def test_invalid_plan_fails_closed(self):
        allocation = AUTONOMY.dynamic_paper_allocation(
            balance=10_000,
            available=10_000,
            current_exposure=0,
            entry_price=0,
            stop_loss=0,
            tp3=0,
            confidence=99,
            risk_score=0,
            profile="HIZLI",
        )
        self.assertFalse(allocation["approved"])
        self.assertEqual(allocation["amount"], 0.0)

    def test_daily_reference_is_explicitly_not_a_guarantee(self):
        progress = AUTONOMY.daily_reference_progress(2.5)
        self.assertEqual(progress["progress_pct"], 50.0)
        self.assertFalse(progress["profit_guaranteed"])
        self.assertIn("garantisi", progress["note"])


if __name__ == "__main__":
    unittest.main()
