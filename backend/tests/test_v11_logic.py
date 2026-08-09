import ast
import asyncio
import json
import math
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace


SOURCE_PATH = Path(__file__).parents[1] / "app" / "main.py"
SOURCE_TEXT = SOURCE_PATH.read_text(encoding="utf-8")
TREE = ast.parse(SOURCE_TEXT)


def load_functions(*names):
    nodes = [
        node for node in TREE.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names
    ]
    namespace = {
        "asyncio": asyncio,
        "datetime": datetime,
        "timezone": timezone,
        "json": json,
        "math": math,
        "FastAPI": object,
        "V9_DEFAULT_UNIVERSE": ("BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"),
    }
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(SOURCE_PATH), "exec"), namespace)
    return namespace


CORE = load_functions(
    "json_safe_payload",
    "empty_v11_risk_state",
    "empty_v10_evolution_state",
    "empty_strategy_orchestrator_state",
    "empty_grid_engine_state",
    "restore_paper_snapshot",
    "v11_returns",
    "v11_std",
    "v11_correlation",
    "v11_correlation_matrix",
    "v11_correlation_clusters",
    "v11_risk_parity_allocations",
    "v11_monte_carlo",
    "v11_stress_scenarios",
    "v11_portfolio_risk_lab",
    "v11_risk_payload",
)


def candles_from_returns(returns, start=100.0):
    rows = []
    price = float(start)
    for index, change in enumerate(returns):
        open_price = price
        close = max(0.1, open_price * (1.0 + float(change)))
        padding = max(open_price, close) * 0.0015
        rows.append({
            "time": index * 900,
            "open": open_price,
            "high": max(open_price, close) + padding,
            "low": min(open_price, close) - padding,
            "close": close,
            "volume": 1_000 + (index % 23) * 17,
        })
        price = close
    return rows


def calm_portfolio(count=430):
    return {
        "BTCUSDT": candles_from_returns([0.00015 + math.sin(i / 7.0) * 0.0011 for i in range(count)]),
        "ETHUSDT": candles_from_returns([0.00012 + math.sin(i / 11.0 + 1.7) * 0.0009 for i in range(count)], 80),
        "SOLUSDT": candles_from_returns([0.00008 + math.sin(i / 5.2 + 3.1) * 0.0008 for i in range(count)], 60),
        "BNBUSDT": candles_from_returns([0.00010 + math.sin(i / 17.0 + 4.4) * 0.0007 for i in range(count)], 120),
    }


def stressed_portfolio(count=430):
    base = []
    for index in range(count):
        shock = -0.065 if index % 37 == 0 and index > 0 else 0.0
        base.append(-0.0005 + math.sin(index / 3.2) * 0.017 + shock)
    return {
        symbol: candles_from_returns([
            change * multiplier + math.sin(index / 13.0 + offset) * 0.0004
            for index, change in enumerate(base)
        ], start)
        for symbol, multiplier, offset, start in (
            ("BTCUSDT", 1.0, 0.1, 100),
            ("ETHUSDT", 1.15, 0.3, 80),
            ("SOLUSDT", 1.35, 0.5, 60),
            ("BNBUSDT", 0.9, 0.7, 120),
        )
    }


class AsyncLock:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class RestorePool:
    async def fetchrow(self, *_args):
        return {"payload": {"portfolio_risk": {
            "enabled": True,
            "busy": True,
            "status": "PORTFÖY RİSKİ İZLENİYOR",
            "cycles": 7,
            "latest_report": {"risk_score": 42, "risk_level": "SARI"},
            "approved_allocations": [{"symbol": "BTCUSDT", "paper_budget_usdt": 900}],
            "orders_enabled": True,
            "testnet_orders_enabled": True,
        }}}


class V11LogicTests(unittest.TestCase):
    def test_json_safe_payload_removes_non_finite_values_recursively(self):
        payload = {
            "ok": 1.25,
            "nan": float("nan"),
            "nested": [float("inf"), {"negative": float("-inf")}],
        }
        safe = CORE["json_safe_payload"](payload)
        self.assertEqual(safe["ok"], 1.25)
        self.assertIsNone(safe["nan"])
        self.assertIsNone(safe["nested"][0])
        self.assertIsNone(safe["nested"][1]["negative"])
        json.dumps(safe, allow_nan=False)

    def test_monte_carlo_is_deterministic_and_tail_metrics_are_ordered(self):
        returns = {symbol: CORE["v11_returns"](rows) for symbol, rows in calm_portfolio().items()}
        weights = {symbol: 0.25 for symbol in returns}
        first = CORE["v11_monte_carlo"](returns, weights, 5_000.0, 24, 500)
        second = CORE["v11_monte_carlo"](returns, weights, 5_000.0, 24, 500)
        self.assertEqual(first, second)
        self.assertGreaterEqual(first["cvar_95_pct"], first["var_95_pct"])
        self.assertEqual(sum(item["count"] for item in first["distribution"]), 500)
        self.assertFalse(first["orders_enabled"])

    def test_risk_parity_is_capped_and_respects_paper_exposure(self):
        returns = {symbol: CORE["v11_returns"](rows) for symbol, rows in calm_portfolio().items()}
        matrix = CORE["v11_correlation_matrix"](returns)
        clusters = CORE["v11_correlation_clusters"](matrix)
        allocation = CORE["v11_risk_parity_allocations"](returns, matrix, clusters, 5_000.0, 0.8)
        self.assertAlmostEqual(sum(item["weight_pct"] for item in allocation), 100.0, delta=0.3)
        self.assertLessEqual(max(item["weight_pct"] for item in allocation), 35.1)
        self.assertAlmostEqual(sum(item["paper_budget_usdt"] for item in allocation), 4_000.0, delta=2.0)
        self.assertTrue(all(item["orders_enabled"] is False for item in allocation))

    def test_highly_correlated_assets_form_a_single_warning_cluster(self):
        shared = [math.sin(index / 4.0) * 0.01 for index in range(360)]
        matrix = CORE["v11_correlation_matrix"]({
            "AAAUSDT": shared,
            "BBBUSDT": [value * 1.2 for value in shared],
            "CCCUSDT": [value * 0.8 for value in shared],
        })
        clusters = CORE["v11_correlation_clusters"](matrix)
        self.assertEqual(clusters[0]["size"], 3)
        self.assertEqual(clusters[0]["status"], "YOĞUNLAŞMA")
        self.assertGreater(matrix["average_abs_correlation_pct"], 99)
        self.assertFalse(matrix["orders_enabled"])

    def test_full_report_contains_stress_gates_and_locked_order_channels(self):
        report = CORE["v11_portfolio_risk_lab"](calm_portfolio(), 5_000.0, "15m", 500, 24)
        self.assertEqual(report["version"], "20.2.0")
        self.assertEqual(len(report["stress_scenarios"]), 4)
        self.assertEqual(len(report["gates"]), 6)
        self.assertEqual(len(report["risk_fingerprint"]), 5)
        self.assertEqual(len(report["allocations"]), 4)
        self.assertFalse(report["orders_enabled"])
        self.assertFalse(report["testnet_orders_enabled"])

    def test_correlated_volatile_portfolio_raises_risk_and_triggers_veto(self):
        calm = CORE["v11_portfolio_risk_lab"](calm_portfolio(), 5_000.0, "15m", 500, 24)
        stressed = CORE["v11_portfolio_risk_lab"](stressed_portfolio(), 5_000.0, "15m", 500, 24)
        self.assertGreater(stressed["risk_score"], calm["risk_score"])
        self.assertTrue(stressed["veto_required"])
        self.assertEqual(stressed["exposure_ratio_pct"], 0)
        self.assertEqual(stressed["invested_budget_usdt"], 0.0)

    def test_public_payload_forces_paper_only_mode(self):
        state = CORE["empty_v11_risk_state"]()
        state["orders_enabled"] = True
        state["testnet_orders_enabled"] = True
        payload = CORE["v11_risk_payload"](state)
        self.assertFalse(payload["orders_enabled"])
        self.assertFalse(payload["testnet_orders_enabled"])
        self.assertEqual(payload["mode"], "PAPER_ONLY")

    def test_source_exposes_v11_and_contains_no_exchange_order_call(self):
        lowered = SOURCE_TEXT.lower()
        self.assertIn('/api/v11/risk', SOURCE_TEXT)
        self.assertIn('/api/v11/risk-lab', SOURCE_TEXT)
        self.assertIn('version="20.2.0"', SOURCE_TEXT)
        self.assertNotIn('/api/v3/order', lowered)
        self.assertNotIn('fapi/v1/order', lowered)
        self.assertNotIn('create_order(', lowered)
        self.assertNotIn('place_order(', lowered)


class V11RestartSafetyTests(unittest.IsolatedAsyncioTestCase):
    async def test_restart_preserves_report_but_requires_manual_reapproval(self):
        paper = {
            "balance": 10_000.0,
            "initial_balance": 10_000.0,
            "positions": [],
            "trades": [],
            "next_id": 1,
            "risk": {},
            "shadow": {},
            "emergency_brake": {},
            "notifications": [],
            "decision_memory": [],
            "grid_plans": [],
            "grid_engine": CORE["empty_grid_engine_state"](),
            "strategy_orchestrator": CORE["empty_strategy_orchestrator_state"](),
            "strategy_evolution": CORE["empty_v10_evolution_state"](),
            "portfolio_risk": CORE["empty_v11_risk_state"](),
            "lock": AsyncLock(),
        }
        app = SimpleNamespace(state=SimpleNamespace(
            db_pool=RestorePool(),
            paper=paper,
            paper_dirty=True,
            infrastructure={"paper_storage": "BEKLENİYOR"},
        ))
        restored = await CORE["restore_paper_snapshot"](app)
        self.assertTrue(restored)
        self.assertFalse(paper["portfolio_risk"]["enabled"])
        self.assertFalse(paper["portfolio_risk"]["busy"])
        self.assertEqual(paper["portfolio_risk"]["cycles"], 7)
        self.assertEqual(paper["portfolio_risk"]["latest_report"]["risk_score"], 42)
        self.assertEqual(paper["portfolio_risk"]["status"], "YENİDEN BAŞLATMA ONAYI")
        self.assertFalse(paper["portfolio_risk"]["orders_enabled"])
        self.assertFalse(paper["portfolio_risk"]["testnet_orders_enabled"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
