import asyncio
import sys
import unittest
from types import SimpleNamespace
from pathlib import Path


ROOT = Path(__file__).parents[2]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.commercial_core import (  # noqa: E402
    FeeGuardInput,
    calculate_fee_guard,
    calculate_grid_guard,
    default_commercial_state,
    hash_password,
    issue_token,
    verify_password,
    verify_token,
)
from app.v22_commercial import sync_v22_storage  # noqa: E402


MAIN_SOURCE = (BACKEND / "app" / "main.py").read_text(encoding="utf-8")
V22_SOURCE = (BACKEND / "app" / "v22_commercial.py").read_text(encoding="utf-8")
CORE_SOURCE = (BACKEND / "app" / "commercial_core.py").read_text(encoding="utf-8")
AGENT_SOURCE = (BACKEND / "v22_agent.py").read_text(encoding="utf-8")
FRONTEND_SOURCE = (ROOT / "frontend" / "src" / "CommercialHub.tsx").read_text(encoding="utf-8")
LOCAL_STORAGE_SOURCE = (BACKEND / "app" / "local_storage.py").read_text(encoding="utf-8")
GITIGNORE_SOURCE = (ROOT / ".gitignore").read_text(encoding="utf-8")


class V22CommercialTests(unittest.TestCase):
    def test_postgres_snapshot_restores_owner_after_runtime_restart(self):
        restored_state = default_commercial_state()
        restored_state["owner_user_id"] = "owner-from-postgres"
        restored_state["users"] = [{"id": "owner-from-postgres", "email": "owner@example.com", "role": "OWNER", "active": True}]

        class SnapshotPool:
            async def execute(self, query, *args):
                return "OK"

            async def fetchrow(self, query, *args):
                return {"payload": restored_state}

        application = SimpleNamespace()
        application.state = SimpleNamespace(
            db_pool=SnapshotPool(),
            v22_commercial={
                "state": default_commercial_state(),
                "storage_lock": asyncio.Lock(),
                "storage_ready": False,
                "restore_attempted": False,
                "storage_status": "YEREL_YEDEK",
            },
        )

        asyncio.run(sync_v22_storage(application))

        runtime = application.state.v22_commercial
        self.assertEqual(runtime["state"]["owner_user_id"], "owner-from-postgres")
        self.assertEqual(runtime["storage_status"], "POSTGRESQL_KALICI")

    def test_passwords_are_scrypt_hashed_and_verified(self):
        record = hash_password("CokGuvenli-Parola-22")
        self.assertTrue(verify_password("CokGuvenli-Parola-22", record))
        self.assertFalse(verify_password("yanlis-parola", record))
        self.assertNotIn("CokGuvenli", str(record))

    def test_tokens_are_signed_typed_and_expiring(self):
        secret = b"v22-test-secret-that-is-long-enough-for-hmac"
        token = issue_token("owner-1", "OWNER", secret, now=1_000, ttl_seconds=120)
        payload = verify_token(token, secret, expected_kind="USER", now=1_050)
        self.assertEqual(payload["sub"], "owner-1")
        with self.assertRaises(ValueError):
            verify_token(token, secret, expected_kind="AGENT", now=1_050)
        with self.assertRaises(ValueError):
            verify_token(token, secret, now=1_121)

    def test_fee_guard_rejects_target_that_does_not_cover_costs(self):
        blocked = calculate_fee_guard(FeeGuardInput(entry=100, target=100.05, notional_usdt=1_000, fee_bps_per_side=4, slippage_bps_per_side=2, minimum_net_usdt=0.25))
        self.assertFalse(blocked["approved"])
        approved = calculate_fee_guard(FeeGuardInput(entry=100, target=101, notional_usdt=1_000, fee_bps_per_side=4, slippage_bps_per_side=2, minimum_net_usdt=0.25))
        self.assertTrue(approved["approved"])
        self.assertGreater(approved["net_usdt"], approved["minimum_required_usdt"])

    def test_short_direction_and_grid_costs_are_supported(self):
        short = calculate_fee_guard(FeeGuardInput(entry=100, target=98, notional_usdt=500, direction="SHORT"))
        self.assertTrue(short["approved"])
        grid = calculate_grid_guard(lower=90, upper=110, grid_count=11, capital_usdt=1_000, maker_share_pct=80)
        self.assertTrue(grid["approved"])
        self.assertGreater(grid["net_cycle_usdt"], 0)

    def test_default_state_can_never_enable_money_or_real_orders(self):
        state = default_commercial_state()
        self.assertTrue(state["security"]["demo_only"])
        self.assertFalse(state["security"]["real_orders_enabled"])
        self.assertFalse(state["security"]["testnet_orders_enabled"])
        self.assertFalse(state["security"]["withdrawals_supported"])
        self.assertFalse(state["security"]["central_exchange_credentials"])
        self.assertFalse(state["billing"]["live"])

    def test_v24_is_wired_into_api_and_interface(self):
        self.assertIn('version="25.0.0"', MAIN_SOURCE)
        self.assertIn("init_v22_commercial(app)", MAIN_SOURCE)
        self.assertIn("v22_commercial_router", MAIN_SOURCE)
        for label in ("Business & Robot Control Center", "Satış Merkezi", "Müşteriler", "Lisans & Ajan", "Net Kâr Koruması", "Yayın Kapısı"):
            self.assertIn(label, FRONTEND_SOURCE)

    def test_v23_tokens_can_be_revoked_with_a_version_bump(self):
        secret = b"v23-test-secret-that-is-long-enough-for-hmac"
        token = issue_token("owner-1", "OWNER", secret, token_version=4, now=2_000)
        payload = verify_token(token, secret, expected_kind="USER", now=2_010)
        self.assertEqual(payload["ver"], 4)

    def test_v23_release_evidence_starts_unverified(self):
        state = default_commercial_state()
        self.assertEqual(state["version"], "25.0.0")
        for key in ("backup", "support", "legal", "security_review"):
            self.assertEqual(state["release_evidence"][key]["status"], "PENDING")

    def test_v23_management_and_operations_endpoints_are_present(self):
        for route in (
            '"/operations"',
            '"/auth/change-password"',
            '"/customers/{user_id}/status"',
            '"/licenses/{license_id}/revoke"',
            '"/agents/{agent_id}/revoke"',
            '"/release-evidence/{evidence_key}"',
        ):
            self.assertIn(route, V22_SOURCE)
        self.assertIn("def monitor", AGENT_SOURCE)
        self.assertIn("HEARTBEAT_SECONDS = 45", AGENT_SOURCE)

    def test_logout_invalidates_existing_sessions_and_persistence_is_configured(self):
        self.assertIn('@router.post("/auth/logout")', V22_SOURCE)
        self.assertIn('user["auth_version"] = int(user.get("auth_version", 1)) + 1', V22_SOURCE)
        self.assertIn("PROTREBOT_DURABLE_AUTH_REQUIRED", V22_SOURCE)
        self.assertIn("PROTREBOT_DURABLE_AUTH_REQUIRED", (ROOT / "render.yaml").read_text(encoding="utf-8"))
        self.assertIn("/auth/logout", FRONTEND_SOURCE)

    def test_owner_registration_is_one_time_and_later_opens_login(self):
        self.assertIn("info.setup_required", FRONTEND_SOURCE)
        self.assertIn("TEK SEFERLİK KAYIT", FRONTEND_SOURCE)
        self.assertIn("HESAP HAZIR", FRONTEND_SOURCE)
        self.assertIn("Bu bilgisayarda beni hatırla", FRONTEND_SOURCE)
        self.assertIn("localStorage", FRONTEND_SOURCE)
        self.assertIn("sessionStorage", FRONTEND_SOURCE)
        self.assertIn("REMEMBER_SESSION_SECONDS", V22_SOURCE)
        self.assertIn("payload.remember", V22_SOURCE)

    def test_owner_and_encrypted_demo_state_use_update_safe_windows_storage(self):
        self.assertIn("LOCALAPPDATA", LOCAL_STORAGE_SOURCE)
        self.assertIn("ProTreBotEliteX", LOCAL_STORAGE_SOURCE)
        self.assertIn("PROTREBOT_DATA_DIR", LOCAL_STORAGE_SOURCE)
        self.assertIn("migrate_legacy_files", V22_SOURCE)

    def test_agent_never_requests_or_transmits_exchange_credentials(self):
        self.assertNotIn("api_key", AGENT_SOURCE.casefold())
        self.assertNotIn("secret_key", AGENT_SOURCE.casefold())
        self.assertIn("fingerprint", AGENT_SOURCE)
        self.assertIn("save_agent_token", AGENT_SOURCE)
        self.assertIn("central_exchange_credentials", CORE_SOURCE)

    def test_v22_secrets_and_runtime_state_are_excluded(self):
        for path in ("v22_commercial_state.json", "v22_server_secret.dat", "v22_agent_token.dat"):
            self.assertIn(path, GITIGNORE_SOURCE)


if __name__ == "__main__":
    unittest.main(verbosity=2)
