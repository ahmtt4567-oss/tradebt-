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
    nodes = [node for node in TREE.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names]
    namespace = {
        "math": math, "datetime": datetime, "timezone": timezone,
        "asyncio": asyncio, "json": json, "FastAPI": object,
        "V9_DEFAULT_UNIVERSE": ("BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"),
    }
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(SOURCE_PATH), "exec"), namespace)
    return namespace


CORE = load_functions(
    "empty_v11_risk_state",
    "empty_strategy_orchestrator_state",
    "empty_grid_engine_state",
    "empty_v10_evolution_state",
    "restore_paper_snapshot",
    "v10_generate_genomes",
    "v10_ema",
    "v10_atr",
    "v10_signal",
    "v10_simulate_genome",
    "v10_market_regime",
    "v10_mutate_champion",
    "v10_build_next_pool",
    "v10_evolution_tournament",
    "v10_evolution_payload",
)


class AsyncLock:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class RestorePool:
    async def fetchrow(self, *_args):
        return {"payload": {"strategy_evolution": {
            "enabled": True, "busy": True, "status": "PAPER EVRİMİ ÇALIŞIYOR",
            "cycles": 11, "active_champion": {"id": "G4-TREND-M2", "label": "Kanıtlı Paper"},
        }}}


def market_candles(count=720):
    rows = []
    price = 100.0
    for index in range(count):
        wave = math.sin(index / 8.5) * 0.25 + math.sin(index / 31) * 0.12
        drift = 0.055 if index < count * 0.68 else 0.025
        open_price = price
        close = max(1.0, open_price + drift + wave)
        rows.append({
            "time": index * 900,
            "open": open_price,
            "high": max(open_price, close) + 0.32,
            "low": min(open_price, close) - 0.32,
            "close": close,
            "volume": 1_000 + (index % 19) * 35,
        })
        price = close
    return rows


class V10LogicTests(unittest.TestCase):
    def test_genome_pool_has_twelve_candidates_and_three_families(self):
        genomes = CORE["v10_generate_genomes"](3)
        self.assertEqual(len(genomes), 12)
        self.assertEqual({item["family"] for item in genomes}, {"GRID", "TREND", "KIRILIM"})
        self.assertTrue(all(item["generation"] == 3 for item in genomes))
        self.assertTrue(all(item["orders_enabled"] is False for item in genomes))

    def test_signal_does_not_read_future_candles(self):
        candles = market_candles()
        genome = next(item for item in CORE["v10_generate_genomes"]() if item["family"] == "TREND")
        index = 300
        before = CORE["v10_signal"](candles[:index + 1], index, genome)
        changed_future = candles[:]
        changed_future[index + 1:] = [
            {**item, "open": 1.0, "high": 50_000.0, "low": 0.5, "close": 40_000.0}
            for item in changed_future[index + 1:]
        ]
        after = CORE["v10_signal"](changed_future, index, genome)
        self.assertEqual(before, after)

    def test_double_cost_cannot_improve_same_genome(self):
        candles = market_candles()
        genome = next(item for item in CORE["v10_generate_genomes"]() if item["family"] == "GRID")
        baseline = CORE["v10_simulate_genome"](candles, genome, 1_000.0, cost_multiplier=1.0, execution_delay=1)
        stressed = CORE["v10_simulate_genome"](candles, genome, 1_000.0, cost_multiplier=2.0, execution_delay=1)
        self.assertEqual(baseline["trades"], stressed["trades"])
        self.assertGreaterEqual(stressed["costs_usdt"], baseline["costs_usdt"])
        self.assertLessEqual(stressed["net_result_usdt"], baseline["net_result_usdt"])
        self.assertFalse(stressed["orders_enabled"])

    def test_tournament_has_walk_forward_overfit_and_paper_gates(self):
        result = CORE["v10_evolution_tournament"](market_candles(), 1_000.0)
        self.assertEqual(result["genome_count"], 12)
        self.assertEqual(len(result["leaderboard"]), 12)
        self.assertEqual(len(result["promotion_gates"]), 7)
        self.assertTrue(all(len(item["folds"]) == 3 for item in result["leaderboard"]))
        self.assertTrue(all(0 <= item["overfit_risk"] <= 99 for item in result["leaderboard"]))
        self.assertTrue(all(item["orders_enabled"] is False for item in result["leaderboard"]))
        self.assertFalse(result["orders_enabled"])
        self.assertFalse(result["testnet_orders_enabled"])

    def test_mutations_are_bounded_and_remain_paper_only(self):
        champion = {"genome": CORE["v10_generate_genomes"]()[5]}
        children = CORE["v10_mutate_champion"](champion, 2)
        self.assertEqual(len(children), 3)
        self.assertTrue(all(item["parent_id"] == champion["genome"]["id"] for item in children))
        self.assertTrue(all(item["generation"] == 2 for item in children))
        self.assertTrue(all(item["params"]["slow"] > item["params"]["fast"] for item in children))
        self.assertTrue(all(item["params"]["target_atr"] > item["params"]["stop_atr"] for item in children))
        self.assertTrue(all(item["orders_enabled"] is False for item in children))

    def test_restart_state_and_public_payload_lock_all_orders(self):
        state = CORE["empty_v10_evolution_state"]()
        state["orders_enabled"] = True
        state["testnet_orders_enabled"] = True
        payload = CORE["v10_evolution_payload"](state)
        self.assertFalse(state["enabled"])
        self.assertFalse(payload["orders_enabled"])
        self.assertFalse(payload["testnet_orders_enabled"])
        self.assertEqual(payload["mode"], "PAPER_ONLY")

    def test_source_exposes_v10_and_contains_no_exchange_order_call(self):
        lowered = SOURCE_TEXT.lower()
        self.assertIn('/api/v10/evolution', SOURCE_TEXT)
        self.assertIn('/api/v10/evolution/rollback', SOURCE_TEXT)
        self.assertIn('version="20.2.0"', SOURCE_TEXT)
        self.assertNotIn('/api/v3/order', lowered)
        self.assertNotIn('fapi/v1/order', lowered)
        self.assertNotIn('create_order(', lowered)


class V10RestartSafetyTests(unittest.IsolatedAsyncioTestCase):
    async def test_restart_preserves_champion_but_forces_manual_reapproval(self):
        paper = {
            "balance": 10_000.0, "initial_balance": 10_000.0, "positions": [], "trades": [],
            "next_id": 1, "risk": {}, "shadow": {}, "emergency_brake": {}, "notifications": [],
            "decision_memory": [], "grid_plans": [], "grid_engine": CORE["empty_grid_engine_state"](),
            "strategy_orchestrator": CORE["empty_strategy_orchestrator_state"](),
            "strategy_evolution": CORE["empty_v10_evolution_state"](), "lock": AsyncLock(),
        }
        app = SimpleNamespace(state=SimpleNamespace(
            db_pool=RestorePool(), paper=paper, paper_dirty=True,
            infrastructure={"paper_storage": "BEKLENİYOR"},
        ))
        restored = await CORE["restore_paper_snapshot"](app)
        self.assertTrue(restored)
        self.assertFalse(paper["strategy_evolution"]["enabled"])
        self.assertFalse(paper["strategy_evolution"]["busy"])
        self.assertEqual(paper["strategy_evolution"]["status"], "YENİDEN BAŞLATMA ONAYI")
        self.assertEqual(paper["strategy_evolution"]["cycles"], 11)
        self.assertEqual(paper["strategy_evolution"]["active_champion"]["id"], "G4-TREND-M2")
        self.assertFalse(paper["strategy_evolution"]["orders_enabled"])
        self.assertFalse(paper["strategy_evolution"]["testnet_orders_enabled"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
