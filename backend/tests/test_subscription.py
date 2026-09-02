import unittest
from datetime import datetime, timedelta, timezone

from app.subscription_core import PLAN_CATALOG, TRIAL_DAYS, active_subscription, entitlement_snapshot


class SubscriptionCoreTests(unittest.TestCase):
    def test_plan_prices_and_entitlements_are_centralized(self):
        self.assertEqual(PLAN_CATALOG["STARTER"]["monthly_price"], 19)
        self.assertEqual(PLAN_CATALOG["STARTER"]["annual_price"], 190)
        self.assertEqual(PLAN_CATALOG["PRO"]["monthly_price"], 39)
        self.assertEqual(PLAN_CATALOG["PRO"]["annual_price"], 390)
        self.assertEqual(PLAN_CATALOG["ELITE"]["monthly_price"], 79)
        self.assertEqual(PLAN_CATALOG["ELITE"]["annual_price"], 790)
        self.assertFalse(PLAN_CATALOG["STARTER"]["entitlements"]["canUseLiveTrading"])
        self.assertTrue(PLAN_CATALOG["PRO"]["entitlements"]["canUseLiveTrading"])
        self.assertTrue(PLAN_CATALOG["ELITE"]["entitlements"]["canUseAdvancedAI"])

    def test_trial_is_seven_days_and_expired_subscription_is_free(self):
        now = datetime.now(timezone.utc)
        state = {"subscriptions": [{"user_id": "user-1", "plan": "STARTER", "status": "TRIAL", "trialEnd": (now + timedelta(days=TRIAL_DAYS)).isoformat()}], "licenses": []}
        snapshot = entitlement_snapshot(state, "user-1")
        self.assertEqual(snapshot["status"], "TRIAL")
        self.assertEqual(snapshot["plan"], "STARTER")
        expired = {"subscriptions": [{"user_id": "user-1", "plan": "PRO", "status": "ACTIVE", "currentPeriodEnd": (now - timedelta(days=1)).isoformat()}], "licenses": []}
        self.assertEqual(entitlement_snapshot(expired, "user-1")["status"], "FREE")

    def test_license_fallback_is_not_an_implicit_frontend_unlock(self):
        state = {"subscriptions": [], "licenses": [{"user_id": "user-1", "plan": "PRO", "status": "ACTIVE", "expires_at": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()}]}
        self.assertIsNone(active_subscription(state, "user-1"))
        self.assertEqual(entitlement_snapshot(state, "user-1")["status"], "FREE")


if __name__ == "__main__":
    unittest.main()
