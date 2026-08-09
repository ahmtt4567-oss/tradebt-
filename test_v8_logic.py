import ast
import math
import unittest
from pathlib import Path


SOURCE_PATH = Path(__file__).parents[1] / "app" / "main.py"
SOURCE_TEXT = SOURCE_PATH.read_text(encoding="utf-8")
TREE = ast.parse(SOURCE_TEXT)


def load_functions(*names):
    nodes = [
        node for node in TREE.body
        if isinstance(node, ast.FunctionDef) and node.name in names
    ]
    namespace = {
        "math": math,
        "INTERVAL_SECONDS": {"1m": 60, "5m": 300, "15m": 900, "1h": 3600, "4h": 14400, "1d": 86400},
        "V8_FORECAST_HORIZONS": (12, 24),
    }
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(SOURCE_PATH), "exec"), namespace)
    return namespace


CORE = load_functions(
    "ema_path",
    "rolling_atr",
    "candle_returns",
    "pearson_correlation",
    "v8_percentile",
    "v8_probability_corridor",
    "v8_calibration_report",
    "v8_chaos_sentinel",
    "v8_execution_twin",
    "v8_portfolio_chaos_test",
    "v8_veto_council",
)


def market_candles(count=520, shock=False):
    rows = []
    price = 100.0
    for index in range(count):
        wave = math.sin(index / 6.5) * 0.16 + math.sin(index / 19) * 0.08
        drift = 0.045
        if shock and index == count - 1:
            drift = -4.8
        open_price = price
        close = max(1.0, open_price + drift + wave)
        extra = 2.4 if shock and index == count - 1 else 0.28
        rows.append({
            "time": index * 900,
            "open": open_price,
            "high": max(open_price, close) + extra,
            "low": min(open_price, close) - extra,
            "close": close,
            "volume": 5_000 if shock and index == count - 1 else 1_000 + (index % 17) * 30,
        })
        price = close
    return rows


def orderbook(spread=2.0, spoof=12.0, pressure=8.0, depth=40_000.0):
    return {
        "mode": "KALICI DUVAR",
        "spread_bps": spread,
        "spoof_risk_score": spoof,
        "pressure_pct": pressure,
        "heatmap": [
            {"notional_usdt": depth / 2},
            {"notional_usdt": depth / 2},
        ],
    }


class V8LogicTests(unittest.TestCase):
    def test_probability_corridor_is_ordered_and_sums_to_one_hundred(self):
        corridor = CORE["v8_probability_corridor"](market_candles(), "15m", 12)
        self.assertEqual(len(corridor["points"]), 12)
        self.assertAlmostEqual(sum(corridor["probabilities"].values()), 100.0, places=1)
        self.assertTrue(all(point["lower"] <= point["base"] <= point["upper"] for point in corridor["points"]))
        self.assertTrue(all(left["time"] < right["time"] for left, right in zip(corridor["points"], corridor["points"][1:])))
        self.assertFalse(corridor["orders_enabled"])

    def test_calibration_produces_out_of_sample_score_and_never_orders(self):
        report = CORE["v8_calibration_report"](market_candles(), "15m", 12)
        self.assertGreaterEqual(report["samples"], 12)
        self.assertGreaterEqual(report["brier_score"], 0.0)
        self.assertLessEqual(report["reliability_score"], 99)
        self.assertTrue(all("outcome" in record for record in report["records"]))
        self.assertFalse(report["orders_enabled"])

    def test_bad_orderbook_and_shock_raise_chaos_score(self):
        calm = CORE["v8_chaos_sentinel"](market_candles(), orderbook())
        stressed = CORE["v8_chaos_sentinel"](
            market_candles(shock=True),
            orderbook(spread=32.0, spoof=88.0, pressure=82.0, depth=500.0),
        )
        self.assertGreater(stressed["chaos_score"], calm["chaos_score"])
        self.assertGreater(stressed["liquidity_shock_score"], calm["liquidity_shock_score"])
        self.assertFalse(stressed["orders_enabled"])

    def test_wide_spread_cannot_improve_execution_twin(self):
        forecast = CORE["v8_probability_corridor"](market_candles(), "15m", 12)
        tight = CORE["v8_execution_twin"](forecast, orderbook(spread=1.5, spoof=8, depth=80_000), 2_000)
        wide = CORE["v8_execution_twin"](forecast, orderbook(spread=35, spoof=80, depth=700), 2_000)
        self.assertGreater(wide["round_trip_cost_pct"], tight["round_trip_cost_pct"])
        self.assertLess(wide["partial_fill_pct"], tight["partial_fill_pct"])
        self.assertFalse(wide["orders_enabled"])

    def test_veto_council_blocks_quarantined_or_chaotic_model(self):
        forecast = CORE["v8_probability_corridor"](market_candles(), "15m", 12)
        execution = CORE["v8_execution_twin"](forecast, orderbook(), 1_000)
        calibration = {"quarantined": True, "status": "MODEL KARANTİNASI", "reliability_score": 18}
        chaos = {"veto_required": True, "level": "YÜKSEK RİSK", "chaos_score": 84}
        portfolio = {"veto_required": False, "level": "TEMKİNLİ", "worst_case_pct": -1.2}
        council = CORE["v8_veto_council"](forecast, calibration, chaos, execution, portfolio)
        self.assertEqual(council["final_action"], "BEKLE")
        self.assertFalse(council["paper_scenario_allowed"])
        self.assertGreaterEqual(council["veto_count"], 2)
        self.assertFalse(council["orders_enabled"])

    def test_portfolio_chaos_test_stays_paper_only(self):
        candles = market_candles()
        orchestrator = {
            "capital": 3_000,
            "allocations": [{"direction": "LONG", "allocated_usdt": 1_200}],
        }
        result = CORE["v8_portfolio_chaos_test"]("ALTUSDT", candles, candles, orchestrator, "LONG")
        self.assertEqual(len(result["scenarios"]), 3)
        self.assertLessEqual(result["safe_allocation_pct"], 40)
        self.assertFalse(result["orders_enabled"])

    def test_source_has_v8_endpoint_and_no_exchange_order_call(self):
        lowered = SOURCE_TEXT.lower()
        self.assertIn('/api/v8/future-lab/{symbol}', SOURCE_TEXT)
        self.assertIn('version="20.2.0"', SOURCE_TEXT)
        self.assertNotIn('/api/v3/order', lowered)
        self.assertNotIn('fapi/v1/order', lowered)
        self.assertNotIn('create_order(', lowered)


if __name__ == "__main__":
    unittest.main(verbosity=2)
