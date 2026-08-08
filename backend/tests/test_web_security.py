import os
import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.web_security import bearer_token, cors_origins, env_flag, evaluate_access


class WebSecurityTests(unittest.TestCase):
    def test_local_mode_can_be_disabled(self):
        decision = evaluate_access(
            required=False, configured_token="", authorization=None,
            path="/api/markets", method="GET",
        )
        self.assertTrue(decision.allowed)

    def test_health_is_public_for_host_monitoring(self):
        decision = evaluate_access(
            required=True, configured_token="x" * 32, authorization=None,
            path="/api/health", method="GET",
        )
        self.assertTrue(decision.allowed)

    def test_missing_server_secret_fails_closed(self):
        decision = evaluate_access(
            required=True, configured_token="short", authorization="Bearer anything",
            path="/api/markets", method="GET",
        )
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.status_code, 503)

    def test_wrong_owner_token_is_rejected(self):
        decision = evaluate_access(
            required=True, configured_token="a" * 32, authorization=f"Bearer {'b' * 32}",
            path="/api/markets", method="GET",
        )
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.status_code, 401)

    def test_correct_owner_token_is_accepted(self):
        token = "owner-preview-token-1234567890"
        decision = evaluate_access(
            required=True, configured_token=token, authorization=f"Bearer {token}",
            path="/api/markets", method="GET",
        )
        self.assertTrue(decision.allowed)

    def test_dedicated_owner_header_does_not_conflict_with_customer_session(self):
        token = "owner-preview-token-1234567890"
        decision = evaluate_access(
            required=True, configured_token=token, authorization="Bearer customer-session",
            owner_access=token, path="/api/v22/me", method="GET",
        )
        self.assertTrue(decision.allowed)

    def test_helpers_normalize_inputs(self):
        self.assertEqual(bearer_token("Bearer abc"), "abc")
        self.assertEqual(cors_origins("https://app.example.com/, https://preview.example.com"), [
            "https://app.example.com", "https://preview.example.com",
        ])
        old = os.environ.get("PROTREBOT_TEST_FLAG")
        try:
            os.environ["PROTREBOT_TEST_FLAG"] = "yes"
            self.assertTrue(env_flag("PROTREBOT_TEST_FLAG"))
        finally:
            if old is None:
                os.environ.pop("PROTREBOT_TEST_FLAG", None)
            else:
                os.environ["PROTREBOT_TEST_FLAG"] = old


if __name__ == "__main__":
    unittest.main()
