import ast
import asyncio
import json
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
        "GRID_ENGINE_FILL_LIMIT": 120,
        "GRID_ENGINE_EVENT_LIMIT": 80,
        "V9_DEFAULT_UNIVERSE": ("BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"),
        "grid_price_decimals": lambda price: 4 if price < 100 else 2,
    }
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(SOURCE_PATH), "exec"), namespace)
    return namespace


CORE = load_functions(
    "empty_v11_risk_state",
    "empty_v10_evolution_state",
    "empty_strategy_orchestrator_state",
    "empty_grid_engine_state",
    "paper_snapshot_data",
    "restore_paper_snapshot",
    "build_grid_variant",
    "grid_level_index",
    "new_live_grid_runtime",
    "append_live_grid_fill",
    "update_live_grid_metrics",
    "process_live_grid_tick",
    "live_twin_decision",
    "grid_runtime_summary",
    "grid_engine_payload",
    "digital_twin_lab",
    "testnet_readiness",
)


def base_plan():
    return {
        "symbol": "BTCUSDT",
        "interval": "15m",
        "mode": "LONG GRID",
        "direction": "LONG",
        "lower": 90.0,
        "upper": 110.0,
        "entry_reference": 100.0,
        "grid_count": 10,
        "grid_step": 2.0,
        "grid_step_pct": 2.0,
        "range_width_pct": 20.0,
        "levels": [90 + 2 * index for index in range(11)],
        "capital": 1_000.0,
        "capital_per_grid": 100.0,
        "max_planned_exposure": 620.0,
        "fee_assumption": {"single_side_pct": 0.10, "round_trip_pct": 0.20, "step_to_fee_multiple": 10, "label": "test"},
        "estimated_per_cycle": {"gross_usdt": 2.0, "fee_usdt": 0.2, "net_usdt": 1.8, "net_edge_pct": 1.8},
        "spread_bps": 2.0,
        "paper_eligible": True,
    }


class AsyncLock:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class RestorePool:
    async def fetchrow(self, *_args):
        return {"payload": {"grid_engine": {"enabled": True, "status": "CANLI PAPER", "profiles": [{"profile": "DENGELİ"}]}}}


class V6LogicTests(unittest.TestCase):
    def test_three_profiles_never_enable_orders(self):
        variants = [CORE["build_grid_variant"](base_plan(), profile) for profile in ("TEMKİNLİ", "DENGELİ", "ATAK")]
        self.assertEqual({item["profile"] for item in variants}, {"TEMKİNLİ", "DENGELİ", "ATAK"})
        self.assertTrue(all(item["orders_enabled"] is False for item in variants))
        self.assertTrue(all(item["inventory_limit"] >= 2 for item in variants))

    def test_live_grid_charges_costs_and_completes_virtual_cycle(self):
        runtime = CORE["new_live_grid_runtime"](CORE["build_grid_variant"](base_plan(), "DENGELİ"), 105.0)
        CORE["process_live_grid_tick"](runtime, 95.0, "2026-08-05T10:00:00+00:00")
        CORE["process_live_grid_tick"](runtime, 105.0, "2026-08-05T10:00:04+00:00")
        self.assertGreaterEqual(runtime["completed_cycles"], 1)
        self.assertGreater(runtime["fees_usdt"], 0)
        self.assertGreater(runtime["slippage_usdt"], 0)
        self.assertTrue(all(fill["paper_only"] for fill in runtime["fills"]))

    def test_inventory_guard_blocks_excess_virtual_entries(self):
        runtime = CORE["new_live_grid_runtime"](CORE["build_grid_variant"](base_plan(), "ATAK"), 110.0)
        runtime["inventory_limit"] = 1
        events = CORE["process_live_grid_tick"](runtime, 90.0, "2026-08-05T10:00:00+00:00")
        self.assertEqual(len(runtime["inventory"]), 1)
        self.assertGreater(runtime["inventory_blocked_count"], 0)
        self.assertTrue(any(event["kind"] == "ENVANTER KİLİDİ" for event in events))

    def test_digital_twin_requires_evidence_before_promotion(self):
        profiles = []
        for name, score, result in (("TEMKİNLİ", 82, 12), ("DENGELİ", 67, 6), ("ATAK", 54, -1)):
            runtime = CORE["new_live_grid_runtime"](CORE["build_grid_variant"](base_plan(), name), 100.0)
            runtime.update({"completed_cycles": 5, "fill_count": 10, "score": score, "marked_result_usdt": result})
            profiles.append(runtime)
        decision = CORE["live_twin_decision"](profiles)
        self.assertEqual(decision["recommended_profile"], "TEMKİNLİ")
        self.assertTrue(decision["promotion_ready"])

        for runtime in profiles:
            runtime["completed_cycles"] = 1
        waiting = CORE["live_twin_decision"](profiles)
        self.assertFalse(waiting["promotion_ready"])
        self.assertEqual(waiting["status"], "VERİ TOPLUYOR")

    def test_historical_twin_lab_is_cost_adjusted_and_order_locked(self):
        def fake_simulation(_candles, plan):
            marked = {"TEMKİNLİ": 12.0, "DENGELİ": 30.0, "ATAK": 16.0}[plan["profile"]]
            return {
                "fills": 12,
                "completed_cycles": 6,
                "marked_result_usdt": marked,
                "fees_usdt": 2.4,
                "max_drawdown_pct": -1.2,
                "open_grids": 1,
                "verdict": "POZİTİF",
            }

        CORE["simulate_grid_plan"] = fake_simulation
        result = CORE["digital_twin_lab"](base_plan(), [{"close": 100.0}] * 50)
        self.assertEqual(len(result["profiles"]), 3)
        self.assertFalse(result["orders_enabled"])
        self.assertEqual(result["winner"], "DENGELİ")
        self.assertTrue(all("slippage_usdt" in item for item in result["profiles"]))

    def test_snapshot_contains_engine_and_testnet_stays_locked(self):
        paper = {
            "balance": 10_000.0,
            "initial_balance": 10_000.0,
            "positions": [],
            "trades": [],
            "next_id": 1,
            "risk": {},
            "grid_engine": {**CORE["empty_grid_engine_state"](), "enabled": True},
        }
        snapshot = CORE["paper_snapshot_data"](paper)
        self.assertIn("grid_engine", snapshot)
        readiness = CORE["testnet_readiness"]()
        self.assertFalse(readiness["orders_enabled"])

    def test_no_exchange_order_endpoint_or_client_call_exists(self):
        lowered = SOURCE_TEXT.lower()
        self.assertNotIn("/api/v3/order", lowered)
        self.assertNotIn("create_order(", lowered)
        self.assertNotIn("fapi/v1/order", lowered)


class V6RestartSafetyTests(unittest.IsolatedAsyncioTestCase):
    async def test_restart_forces_manual_reapproval(self):
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
        self.assertFalse(paper["grid_engine"]["enabled"])
        self.assertEqual(paper["grid_engine"]["status"], "YENİDEN BAŞLATMA ONAYI")


if __name__ == "__main__":
    unittest.main(verbosity=2)
