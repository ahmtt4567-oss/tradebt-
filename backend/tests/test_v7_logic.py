import ast
import asyncio
import json
import math
import os
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace


SOURCE_PATH = Path(__file__).parents[1] / "app" / "main.py"
SOURCE_TEXT = SOURCE_PATH.read_text(encoding="utf-8")
TREE = ast.parse(SOURCE_TEXT)


def load_functions(*names):
    nodes = [node for node in TREE.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names]
    namespace = {
        "asyncio": asyncio,
        "datetime": datetime,
        "timezone": timezone,
        "json": json,
        "os": os,
        "FastAPI": object,
        "V7_STRATEGIES": ("GRID", "TREND", "KIRILIM"),
        "V7_ORCHESTRATOR_EVENT_LIMIT": 100,
        "V9_DEFAULT_UNIVERSE": ("BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"),
    }
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(SOURCE_PATH), "exec"), namespace)
    return namespace


CORE = load_functions(
    "empty_v11_risk_state",
    "empty_v10_evolution_state",
    "empty_grid_engine_state",
    "empty_strategy_orchestrator_state",
    "paper_snapshot_data",
    "restore_paper_snapshot",
    "ema_path",
    "rolling_atr",
    "simulate_v7_strategy",
    "v7_market_replay",
    "candle_returns",
    "pearson_correlation",
    "v7_strategy_council",
    "v7_allocate_capital",
    "v7_orchestrator_payload",
)


def trending_candles(count=740):
    rows = []
    price = 100.0
    for index in range(count):
        wave = math.sin(index / 7) * 0.22
        open_price = price
        close = open_price + 0.12 + wave
        rows.append({
            "time": index * 900,
            "open": open_price,
            "high": max(open_price, close) + 0.35,
            "low": min(open_price, close) - 0.35,
            "close": close,
            "volume": 1_000 + (index % 17) * 35,
        })
        price = close
    return rows


def range_candles(count=740):
    rows = []
    for index in range(count):
        center = 100 + math.sin(index / 5) * 3.2
        open_price = 100 + math.sin((index - 1) / 5) * 3.2
        rows.append({
            "time": index * 900,
            "open": open_price,
            "high": max(open_price, center) + 0.45,
            "low": min(open_price, center) - 0.45,
            "close": center,
            "volume": 1_100 + (index % 13) * 25,
        })
    return rows


class AsyncLock:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class RestorePool:
    async def fetchrow(self, *_args):
        return {"payload": {
            "strategy_orchestrator": {
                "enabled": True,
                "status": "CANLI PAPER ORKESTRA",
                "cycles": 9,
                "universe": ["BTCUSDT"],
            },
        }}


class V7LogicTests(unittest.TestCase):
    def test_replay_compares_three_strategies_and_never_enables_orders(self):
        replay = CORE["v7_market_replay"](range_candles(), "7d", 3_000.0)
        self.assertEqual({item["strategy"] for item in replay["profiles"]}, {"GRID", "TREND", "KIRILIM"})
        self.assertFalse(replay["orders_enabled"])
        self.assertTrue(all(len(item["stress_cases"]) == 3 for item in replay["profiles"]))
        self.assertTrue(all(item["orders_enabled"] is False for item in replay["profiles"]))

    def test_double_cost_stress_cannot_improve_same_strategy_result(self):
        candles = trending_candles()
        baseline = CORE["simulate_v7_strategy"](candles, "TREND", 2_000.0)
        stressed = CORE["simulate_v7_strategy"](candles, "TREND", 2_000.0, cost_multiplier=2.0)
        self.assertEqual(baseline["trades"], stressed["trades"])
        self.assertGreaterEqual(stressed["costs_usdt"], baseline["costs_usdt"])
        self.assertLessEqual(stressed["net_result_usdt"], baseline["net_result_usdt"])

    def test_strategy_council_quarantines_only_with_enough_negative_evidence(self):
        rows = []
        for symbol in ("AAAUSDT", "BBBUSDT", "CCCUSDT"):
            profiles = []
            for strategy in ("GRID", "TREND", "KIRILIM"):
                profiles.append({
                    "strategy": strategy,
                    "trades": 8,
                    "certified": strategy != "GRID",
                    "net_return_pct": -1.2 if strategy == "GRID" else 1.0,
                    "ranking_score": 42 if strategy == "GRID" else 70,
                    "max_drawdown_pct": -3.0,
                })
            rows.append({"symbol": symbol, "replay_profiles": profiles})
        council, quarantined = CORE["v7_strategy_council"](rows)
        self.assertIn("GRID", quarantined)
        self.assertNotIn("TREND", quarantined)
        self.assertTrue(next(item for item in council if item["strategy"] == "GRID")["quarantined"])

    def test_allocator_blocks_highly_correlated_same_direction_candidate(self):
        shared = [math.sin(index / 5) / 100 for index in range(60)]
        rows = [
            {"symbol": "AAAUSDT", "strategy": "TREND", "direction": "LONG", "confidence": 90, "risk_score": 20, "allocation_ready": True, "return_fingerprint": shared},
            {"symbol": "BBBUSDT", "strategy": "TREND", "direction": "LONG", "confidence": 85, "risk_score": 22, "allocation_ready": True, "return_fingerprint": shared},
            {"symbol": "CCCUSDT", "strategy": "GRID", "direction": "NÖTR", "confidence": 72, "risk_score": 30, "allocation_ready": True, "return_fingerprint": list(reversed(shared))},
        ]
        allocation = CORE["v7_allocate_capital"](rows, 3_000.0)
        locked = next(item for item in allocation["allocations"] if item["symbol"] == "BBBUSDT")
        self.assertEqual(locked["status"], "KORELASYON KİLİDİ")
        self.assertEqual(locked["allocated_usdt"], 0.0)
        self.assertLessEqual(allocation["heat_pct"], 100)
        self.assertFalse(allocation["orders_enabled"])

    def test_allocator_immediately_zeroes_newly_quarantined_strategy(self):
        rows = [{
            "symbol": "AAAUSDT", "strategy": "GRID", "direction": "NÖTR",
            "confidence": 88, "risk_score": 16, "allocation_ready": True,
            "return_fingerprint": [0.001] * 60,
        }]
        allocation = CORE["v7_allocate_capital"](rows, 3_000.0, ["GRID"])
        blocked = allocation["allocations"][0]
        self.assertEqual(blocked["status"], "STRATEJİ KARANTİNASI")
        self.assertEqual(blocked["allocated_usdt"], 0.0)
        self.assertEqual(allocation["heat_pct"], 0.0)

    def test_public_payload_removes_return_fingerprints(self):
        engine = {
            **CORE["empty_strategy_orchestrator_state"](),
            "symbols": [{"symbol": "BTCUSDT", "return_fingerprint": [0.1], "strategy": "BEKLE"}],
        }
        payload = CORE["v7_orchestrator_payload"](engine)
        self.assertNotIn("return_fingerprint", payload["symbols"][0])
        self.assertFalse(payload["orders_enabled"])

    def test_snapshot_contains_v7_and_source_has_no_exchange_order_call(self):
        paper = {
            "balance": 10_000.0,
            "initial_balance": 10_000.0,
            "positions": [],
            "trades": [],
            "next_id": 1,
            "risk": {},
            "strategy_orchestrator": {**CORE["empty_strategy_orchestrator_state"](), "enabled": True},
        }
        snapshot = CORE["paper_snapshot_data"](paper)
        self.assertIn("strategy_orchestrator", snapshot)
        lowered = SOURCE_TEXT.lower()
        self.assertNotIn("/api/v3/order", lowered)
        self.assertNotIn("create_order(", lowered)
        self.assertNotIn("fapi/v1/order", lowered)
        self.assertIn('version="20.2.0"', SOURCE_TEXT)


class V7RestartSafetyTests(unittest.IsolatedAsyncioTestCase):
    async def test_restart_disables_orchestrator_until_manual_approval(self):
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
            "lock": AsyncLock(),
        }
        app = SimpleNamespace(state=SimpleNamespace(
            db_pool=RestorePool(), paper=paper, paper_dirty=True,
            infrastructure={"paper_storage": "BEKLENİYOR"},
        ))
        restored = await CORE["restore_paper_snapshot"](app)
        self.assertTrue(restored)
        self.assertFalse(paper["strategy_orchestrator"]["enabled"])
        self.assertEqual(paper["strategy_orchestrator"]["status"], "YENİDEN BAŞLATMA ONAYI")
        self.assertEqual(paper["strategy_orchestrator"]["cycles"], 9)


if __name__ == "__main__":
    unittest.main(verbosity=2)
