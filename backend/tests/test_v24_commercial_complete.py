import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[2]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.commerce_core import (  # noqa: E402
    calculate_demo_invoice,
    default_business_settings,
    launch_checklist,
    sanitize_business_settings,
)
from app.commercial_core import default_commercial_state  # noqa: E402


ROUTER_SOURCE = (BACKEND / "app" / "v24_commerce.py").read_text(encoding="utf-8")
MAIN_SOURCE = (BACKEND / "app" / "main.py").read_text(encoding="utf-8")
FRONTEND_SOURCE = (ROOT / "frontend" / "src" / "CommerceCenter.tsx").read_text(encoding="utf-8")


class V24CommercialCompleteTests(unittest.TestCase):
    def test_default_state_contains_full_commercial_launch_lab(self):
        state = default_commercial_state()
        self.assertEqual(state["version"], "25.0.0")
        for key in ("business", "leads", "demo_invoices", "support_tickets", "acceptances"):
            self.assertIn(key, state)
        self.assertFalse(state["business"]["checkout_live"])
        self.assertFalse(state["business"]["card_data_collected"])

    def test_business_settings_cannot_restore_live_billing(self):
        settings = sanitize_business_settings({
            "brand_name": "Demo Marka",
            "currency": "TRY",
            "trial_days": 999,
            "payment_provider": "LIVE_PROVIDER",
            "checkout_live": True,
            "card_data_collected": True,
        })
        self.assertEqual(settings["brand_name"], "Demo Marka")
        self.assertEqual(settings["currency"], "TRY")
        self.assertEqual(settings["trial_days"], 90)
        self.assertEqual(settings["payment_provider"], "NOT_CONFIGURED")
        self.assertFalse(settings["checkout_live"])
        self.assertFalse(settings["card_data_collected"])

    def test_demo_invoice_calculates_discount_and_tax_without_collecting_money(self):
        result = calculate_demo_invoice(
            plan_code="PRO",
            plan={"name": "Profesyonel", "monthly_usd": 79},
            months=3,
            discount_pct=10,
            tax_pct=20,
            currency="USD",
        )
        self.assertEqual(result["subtotal"], 237.0)
        self.assertEqual(result["discount"], 23.7)
        self.assertEqual(result["tax"], 42.66)
        self.assertEqual(result["total"], 255.96)
        self.assertEqual(result["payment_status"], "DEMO_PREVIEW")
        self.assertFalse(result["collects_money"])

    def test_launch_checklist_keeps_payment_external_and_pending(self):
        settings = default_business_settings()
        checklist = launch_checklist(settings, {})
        payment = next(item for item in checklist if item["key"] == "billing")
        self.assertFalse(payment["passed"])
        self.assertIn("sağlayıcı", payment["detail"])

    def test_v24_routes_and_modern_tabs_are_integrated(self):
        self.assertIn("v24_commerce_router", MAIN_SOURCE)
        for route in ('"/overview"', '"/settings"', '"/leads"', '"/invoice-preview"', '"/acceptance"', '"/support"', '"/customer-home"'):
            self.assertIn(route, ROUTER_SOURCE)
        for label in ("V24 · COMMERCIAL COMPLETE", "Satış Hunisi", "Paket & Teklif", "Destek", "YAYIN HAZIRLIĞI"):
            self.assertIn(label, FRONTEND_SOURCE)

    def test_v24_commerce_router_never_accepts_card_or_exchange_secrets(self):
        lowered = ROUTER_SOURCE.casefold()
        for forbidden in ("card_number", "cvv", "api_key", "secret_key", "withdraw", "place_order"):
            self.assertNotIn(forbidden, lowered)
        self.assertIn('"checkout_live": false', lowered)
        self.assertIn('"collects_card_data": false', lowered)


if __name__ == "__main__":
    unittest.main(verbosity=2)
