import sys
import time
import unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import AsyncMock, patch


BACKEND = Path(__file__).parents[1]
sys.path.insert(0, str(BACKEND))

from app.execution_core import HARD_MAX_POSITIONS, evaluate_entry_gates, sanitize_execution_policy  # noqa: E402
from app.v25_execution import automatic_cycle, initial_state, rank_market_tickers  # noqa: E402


class MultiSymbolScannerTests(unittest.TestCase):
    def test_scanner_filters_contract_status_assets_liquidity_and_activity(self):
        exchange_info = {"symbols": [
            {"symbol": "BTCUSDT", "status": "TRADING", "contractType": "PERPETUAL", "quoteAsset": "USDT"},
            {"symbol": "ETHUSDT", "status": "BREAK", "contractType": "PERPETUAL", "quoteAsset": "USDT"},
            {"symbol": "USDCUSDT", "status": "TRADING", "contractType": "PERPETUAL", "quoteAsset": "USDT"},
            {"symbol": "SOLUPUSDT", "status": "TRADING", "contractType": "PERPETUAL", "quoteAsset": "USDT"},
            {"symbol": "BNBUSDT", "status": "TRADING", "contractType": "PERPETUAL", "quoteAsset": "USDT"},
        ]}
        tickers = [
            {"symbol": "BTCUSDT", "lastPrice": "100", "quoteVolume": "20000000", "priceChangePercent": "3"},
            {"symbol": "ETHUSDT", "lastPrice": "100", "quoteVolume": "20000000", "priceChangePercent": "3"},
            {"symbol": "USDCUSDT", "lastPrice": "1", "quoteVolume": "20000000", "priceChangePercent": "3"},
            {"symbol": "SOLUPUSDT", "lastPrice": "1", "quoteVolume": "20000000", "priceChangePercent": "3"},
            {"symbol": "BNBUSDT", "lastPrice": "100", "quoteVolume": "100", "priceChangePercent": "3"},
        ]
        result = rank_market_tickers(exchange_info, tickers)
        self.assertEqual([item["symbol"] for item in result], ["BTCUSDT"])

    def test_scanner_selects_top_candidates_and_excludes_occupied_symbols(self):
        symbols = [f"COIN{index}USDT" for index in range(30)]
        exchange_info = {"symbols": [
            {"symbol": symbol, "status": "TRADING", "contractType": "PERPETUAL", "quoteAsset": "USDT"}
            for symbol in symbols
        ]}
        tickers = [
            {"symbol": symbol, "lastPrice": "100", "quoteVolume": str(1_000_000 + index * 1_000_000), "priceChangePercent": str(index + 1)}
            for index, symbol in enumerate(symbols)
        ]
        result = rank_market_tickers(exchange_info, tickers, candidate_limit=25, excluded_symbols={"COIN29USDT"})
        self.assertEqual(len(result), 25)
        self.assertNotIn("COIN29USDT", {item["symbol"] for item in result})
        self.assertEqual(result[0]["symbol"], "COIN28USDT")

    def test_position_ceiling_is_five_and_gate_blocks_the_sixth(self):
        self.assertEqual(HARD_MAX_POSITIONS, 5)
        policy = sanitize_execution_policy({"max_positions": 5, "allowed_symbols": ["BTCUSDT"]})
        result = evaluate_entry_gates(
            symbol="BTCUSDT",
            signal={"direction": "LONG", "confidence": 95, "radar": {"trap_score": 10}},
            snapshot={"positions": [{"symbol": f"COIN{index}USDT"} for index in range(5)], "open_orders": [], "hedge_mode": False},
            policy=policy,
            daily={"entries": 0, "realized_pnl": 0, "unverified_closures": 0},
            spread_bps=1,
            armed=True,
            allowed_symbols=["BTCUSDT"],
        )
        failed = {item["key"] for item in result["gates"] if not item["passed"]}
        self.assertIn("positions", failed)

    def test_automatic_cycle_calls_scanner_when_automation_is_active(self):
        state = initial_state()
        state["auto"].update({"enabled": True, "session_until": time.time() + 3600})
        application = SimpleNamespace(state=SimpleNamespace(v25_execution=state))
        client = SimpleNamespace(last_scan_eligible_count=7)
        with patch("app.v25_execution.readiness", return_value={"ready": True}), \
                patch("app.v25_execution.client_for", return_value=client), \
                patch("app.v25_execution.account_snapshot", new=AsyncMock(return_value={"positions": [], "open_orders": []})), \
                patch("app.v25_execution.live_daily_metrics", return_value={"entries": 0, "realized_pnl": 0, "unverified_closures": 0}), \
                patch("app.v25_execution.scan_market_candidates", new=AsyncMock(return_value=[])) as scan, \
                patch("app.v25_execution.persist_state"):
            import asyncio
            asyncio.run(automatic_cycle(application))
        scan.assert_awaited_once_with(client, {"positions": [], "open_orders": []})
        self.assertEqual(state["auto"]["last_scan_stats"]["deep_analysis_candidates"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)