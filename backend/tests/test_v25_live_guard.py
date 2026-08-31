import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).parents[2]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.execution_core import (  # noqa: E402
    HARD_MAX_DAILY_LOSS_USDT,
    HARD_MAX_LEVERAGE,
    HARD_MAX_MARGIN_USDT,
    HARD_MAX_POSITIONS,
    credential_fingerprint,
    daily_execution_metrics,
    evaluate_entry_gates,
    policy_digest,
    release_gates,
    release_ready,
    risk_sized_order,
    sanitize_execution_policy,
)


EXECUTION_SOURCE = (BACKEND / "app" / "v25_execution.py").read_text(encoding="utf-8")
CORE_SOURCE = (BACKEND / "app" / "execution_core.py").read_text(encoding="utf-8")
CREDENTIAL_SOURCE = (BACKEND / "app" / "credential_store.py").read_text(encoding="utf-8")
MAIN_SOURCE = (BACKEND / "app" / "main.py").read_text(encoding="utf-8")
FRONTEND_SOURCE = (ROOT / "ExecutionCenter.tsx").read_text(encoding="utf-8")
ACTIVE_COMMERCIAL_SOURCE = (ROOT / "CommercialHub.tsx").read_text(encoding="utf-8")
ACTIVE_EXECUTION_SOURCE = (ROOT / "ExecutionCenter.tsx").read_text(encoding="utf-8")
ACTIVE_API_SOURCE = (ROOT / "api.ts").read_text(encoding="utf-8")
VERCEL_SOURCE = (ROOT / "vercel.json").read_text(encoding="utf-8")
RENDER_SOURCE = (ROOT / "render.yaml").read_text(encoding="utf-8")


class V25LiveGuardCoreTests(unittest.TestCase):
    def test_restore_sanitizer_cannot_exceed_hard_caps(self):
        policy = sanitize_execution_policy({
            "max_margin_per_trade": 9999,
            "max_leverage": 125,
            "max_positions": 999,
            "daily_loss_limit": 9999,
            "allowed_symbols": ["BTC/USDT", "ETHUSDT", "BAD-USD"],
        })
        self.assertEqual(policy["max_margin_per_trade"], HARD_MAX_MARGIN_USDT)
        self.assertEqual(policy["max_leverage"], HARD_MAX_LEVERAGE)
        self.assertEqual(policy["max_positions"], HARD_MAX_POSITIONS)
        self.assertEqual(policy["daily_loss_limit"], HARD_MAX_DAILY_LOSS_USDT)
        self.assertEqual(policy["allowed_symbols"], ["BTCUSDT", "ETHUSDT"])

    def test_policy_digest_changes_when_risk_changes(self):
        first = sanitize_execution_policy({})
        second = sanitize_execution_policy({"max_margin_per_trade": 30})
        self.assertNotEqual(policy_digest(first), policy_digest(second))

    def test_risk_sizing_respects_loss_margin_and_leverage(self):
        policy = sanitize_execution_policy({"max_margin_per_trade": 25, "max_loss_per_trade": 3, "max_leverage": 2})
        order = risk_sized_order(100, 98, policy)
        self.assertLessEqual(order["margin_usdt"], 25)
        self.assertLessEqual(order["notional_usdt"], 50)
        self.assertLessEqual(order["estimated_stop_loss_usdt"], 3)
        with self.assertRaises(ValueError):
            risk_sized_order(100, 90, policy)

    def test_entry_gate_fails_closed_without_arm_and_on_duplicate(self):
        policy = sanitize_execution_policy({"min_confidence": 85, "max_positions": 2})
        result = evaluate_entry_gates(
            symbol="BTCUSDT",
            signal={"direction": "LONG", "confidence": 92, "radar": {"trap_score": 20}},
            snapshot={"positions": [{"symbol": "BTCUSDT"}], "open_orders": [], "hedge_mode": False},
            policy=policy,
            daily={"entries": 0, "realized_pnl": 0},
            spread_bps=1.5,
            armed=False,
        )
        self.assertFalse(result["passed"])
        failed = {item["key"] for item in result["gates"] if not item["passed"]}
        self.assertIn("arm", failed)
        self.assertIn("duplicate", failed)

    def test_open_loss_uses_same_hard_daily_loss_circuit_breaker(self):
        policy = sanitize_execution_policy({"daily_loss_limit": 10})
        result = evaluate_entry_gates(
            symbol="BTCUSDT",
            signal={"direction": "LONG", "confidence": 95, "radar": {"trap_score": 10}},
            snapshot={"positions": [], "open_orders": [], "hedge_mode": False, "unrealized_pnl": -10.01},
            policy=policy,
            daily={"entries": 0, "realized_pnl": 0, "unverified_closures": 0},
            spread_bps=1,
            armed=True,
        )
        failed = {item["key"] for item in result["gates"] if not item["passed"]}
        self.assertIn("open_loss", failed)

    def test_release_requires_every_gate_and_demo_certificate(self):
        locked = release_gates(credentials=True, consent_active=True, connected=True, one_way=True, policy_acknowledged=True, demo_certificate={"status": "KANIT TOPLUYOR", "score": 75})
        self.assertFalse(release_ready(locked))
        ready = release_gates(credentials=True, consent_active=True, connected=True, one_way=True, policy_acknowledged=True, demo_certificate={"status": "DEMO SERTİFİKALI", "score": 100})
        self.assertTrue(release_ready(ready))

    def test_daily_metrics_count_only_live_entries_and_closed_realized(self):
        events = [
            {"kind": "LIVE_ENTRY", "created_at": "2026-08-08T10:00:00+00:00"},
            {"kind": "LIVE_POSITION_CLOSED", "created_at": "2026-08-08T11:00:00+00:00", "realized_pnl": -2.5},
            {"kind": "DEMO_ENTRY", "created_at": "2026-08-08T12:00:00+00:00"},
        ]
        metrics = daily_execution_metrics(events, datetime(2026, 8, 8, 15, tzinfo=timezone.utc))
        self.assertEqual(metrics["entries"], 1)
        self.assertEqual(metrics["realized_pnl"], -2.5)
        self.assertEqual(metrics["unverified_closures"], 0)

    def test_unverified_close_blocks_until_exchange_pnl_is_proven(self):
        events = [
            {"kind": "LIVE_POSITION_CLOSED_UNVERIFIED", "plan_id": "plan-1", "created_at": "2026-08-08T10:00:00+00:00"},
        ]
        pending = daily_execution_metrics(events, datetime(2026, 8, 8, 15, tzinfo=timezone.utc))
        self.assertEqual(pending["unverified_closures"], 1)
        events.append({"kind": "LIVE_POSITION_CLOSED", "plan_id": "plan-1", "realized_pnl": -1.25, "created_at": "2026-08-08T10:01:00+00:00"})
        verified = daily_execution_metrics(events, datetime(2026, 8, 8, 15, tzinfo=timezone.utc))
        self.assertEqual(verified["unverified_closures"], 0)

    def test_key_fingerprint_is_one_way_and_stable(self):
        first = credential_fingerprint("live-api-key-123456")
        self.assertEqual(first, credential_fingerprint("live-api-key-123456"))
        self.assertNotIn("live-api-key", first or "")

class V25LiveGuardIntegrationContractTests(unittest.TestCase):
    def test_live_transport_is_separate_and_official_host_allowlisted(self):
        self.assertIn('LIVE_REST_BASE = "https://fapi.binance.com"', EXECUTION_SOURCE)
        self.assertIn('LIVE_WS_BASE = "wss://fstream.binance.com/private"', EXECUTION_SOURCE)
        self.assertIn("PRIVATE_PATHS", EXECUTION_SOURCE)
        for forbidden in ("withdraw", "deposit", "transfer"):
            self.assertNotIn(f'/sapi/v1/{forbidden}', EXECUTION_SOURCE.casefold())

    def test_unknown_execution_is_queried_not_blindly_retried(self):
        self.assertIn("unknown_execution", EXECUTION_SOURCE)
        self.assertIn("origClientOrderId", EXECUTION_SOURCE)
        self.assertIn("find_order", EXECUTION_SOURCE)
        self.assertNotIn("for attempt in", EXECUTION_SOURCE)

    def test_crash_window_persists_full_intent_and_recovers_orphan_plan(self):
        self.assertIn('"spec": serializable_spec', EXECUTION_SOURCE)
        self.assertIn("recover_plan_from_intent", EXECUTION_SOURCE)
        self.assertIn("recover_orphan_plans", EXECUTION_SOURCE)
        self.assertIn("await recover_orphan_plans(client, state, positions)", EXECUTION_SOURCE)
        self.assertIn("Persist exchange acceptance before any later API call", EXECUTION_SOURCE)

    def test_private_user_stream_and_verified_pnl_fallback_exist(self):
        self.assertIn("live_user_stream_loop", EXECUTION_SOURCE)
        self.assertIn('("POST", "/fapi/v1/listenKey")', EXECUTION_SOURCE)
        self.assertIn('"/fapi/v1/userTrades"', EXECUTION_SOURCE)
        self.assertIn("LIVE_POSITION_CLOSED_UNVERIFIED", EXECUTION_SOURCE)
        self.assertIn("funding_included", EXECUTION_SOURCE)

    def test_closed_pnl_is_attributed_by_exact_order_identity(self):
        self.assertIn('"/fapi/v1/allOrders"', EXECUTION_SOURCE)
        self.assertIn('"/fapi/v1/allAlgoOrders"', EXECUTION_SOURCE)
        self.assertIn("actualOrderId", EXECUTION_SOURCE)
        self.assertIn("expected_normal_clients", EXECUTION_SOURCE)
        self.assertIn("in known_ids", EXECUTION_SOURCE)

    def test_real_entries_require_readiness_and_short_lived_arm(self):
        self.assertIn("LIVE_ARM_SECONDS = 5 * 60", EXECUTION_SOURCE)
        self.assertIn('if not is_armed(state)', EXECUTION_SOURCE)
        self.assertIn('if not readiness(application, state)["ready"]', EXECUTION_SOURCE)
        self.assertIn("30 gün / 100 Demo işlem kanıtı", CORE_SOURCE)
        self.assertIn("LIVE_AUTO_SESSION_SECONDS = 60 * 60", EXECUTION_SOURCE)
        self.assertIn('state["policy"]["scan_seconds"]', EXECUTION_SOURCE)

    def test_stop_failure_closes_with_reduce_only_and_emergency_is_scoped(self):
        self.assertIn('"reduceOnly": "true"', EXECUTION_SOURCE)
        self.assertIn("STOP BAŞARISIZ · KAPATILIYOR", EXECUTION_SOURCE)
        self.assertIn("startswith(LIVE_CLIENT_PREFIX)", EXECUTION_SOURCE)
        self.assertIn("active_symbols", EXECUTION_SOURCE)
        self.assertIn("cancel_owned_algos_for_symbol", EXECUTION_SOURCE)
        self.assertIn("PROTECTION_CLEANUP", EXECUTION_SOURCE)

    def test_credentials_are_dpapi_only_and_never_browser_inputs(self):
        self.assertIn("LIVE_VAULT_PATH", CREDENTIAL_SOURCE)
        self.assertIn("CryptProtectData", CREDENTIAL_SOURCE)
        lowered = (FRONTEND_SOURCE + ACTIVE_COMMERCIAL_SOURCE).casefold()
        self.assertNotIn("secret_key", lowered)
        self.assertNotIn("api_key", lowered)
        self.assertIn("protrebot-v25-session", ACTIVE_COMMERCIAL_SOURCE)
        self.assertIn("secret_inputs_in_browser", EXECUTION_SOURCE)

    def test_v25_router_and_frontend_center_are_integrated(self):
        self.assertIn('version="25.0.0"', MAIN_SOURCE)
        self.assertIn("httpx.AsyncClient(timeout=15, trust_env=False)", MAIN_SOURCE)
        self.assertIn("v25_execution_router", MAIN_SOURCE)
        for route in ('"/connect/read-only"', '"/market/candles"', '"/policy"', '"/order/test"', '"/arm"', '"/order"', '"/auto/start"', '"/emergency"'):
            self.assertIn(route, EXECUTION_SOURCE)
        for label in ("Canlı Kasa & Otonom Emir Merkezi", "Canlı Risk Politikası", "Canlı Yayın Kapısı", "MARKET / LIMIT Emir Bileti", "Canlı Seviye Grafiği", "ACİL DURDUR"):
            self.assertIn(label, FRONTEND_SOURCE)

    def test_active_frontend_loading_has_timeout_error_and_retry_paths(self):
        for source in (ACTIVE_COMMERCIAL_SOURCE, ACTIVE_EXECUTION_SOURCE):
            self.assertIn("API_TIMEOUT_MS = 15000", source)
            self.assertIn("controller.abort()", source)
            self.assertIn("finally { window.clearTimeout(timeout) }", source)
            self.assertIn("TEKRAR DENE", source)
        self.assertIn("setLoadError", ACTIVE_COMMERCIAL_SOURCE)
        self.assertIn("setLoadError", ACTIVE_EXECUTION_SOURCE)
        self.assertIn("V25 Live Guard geçersiz yanıt döndürdü", ACTIVE_EXECUTION_SOURCE)

    def test_active_v25_requests_forward_the_verified_owner_access_header(self):
        self.assertIn("'/api/v22', '/api/v24'", ACTIVE_API_SOURCE)
        self.assertNotIn("'/api/v25'", ACTIVE_API_SOURCE)
        self.assertIn("X-ProTreBot-Owner", ACTIVE_API_SOURCE)
        self.assertIn("ownerAccessToken()", ACTIVE_API_SOURCE)

    def test_vercel_build_targets_current_render_api(self):
        self.assertIn('"VITE_API_URL": "https://tradebt15.onrender.com"', VERCEL_SOURCE)
        self.assertNotIn("tradebt8.onrender.com", VERCEL_SOURCE)

    def test_render_manifest_matches_production_service(self):
        self.assertIn("name: tradebt15", RENDER_SOURCE)
        self.assertIn("startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT", RENDER_SOURCE)

    def test_manual_live_order_requires_second_explicit_confirmation(self):
        self.assertIn("class ManualLiveOrderRequest", EXECUTION_SOURCE)
        self.assertIn("CANLI EMİR GÖNDER", EXECUTION_SOURCE)
        self.assertIn("confirmation:phrase", FRONTEND_SOURCE)


if __name__ == "__main__":
    unittest.main(verbosity=2)
