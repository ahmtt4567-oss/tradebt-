import ast
import hashlib
import hmac
import re
import unittest
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP
from pathlib import Path
from urllib.parse import urlencode


ROOT = Path(__file__).parents[2]
SOURCE_PATH = ROOT / "backend" / "app" / "binance_demo.py"
SOURCE_TEXT = SOURCE_PATH.read_text(encoding="utf-8")
ROOT_SOURCE_TEXT = (ROOT / "binance_demo.py").read_text(encoding="utf-8")
MAIN_TEXT = (ROOT / "backend" / "app" / "main.py").read_text(encoding="utf-8")
FRONTEND_TEXT = (ROOT / "frontend" / "src" / "BinanceDemo.tsx").read_text(encoding="utf-8")
STYLE_TEXT = (ROOT / "frontend" / "src" / "binance-demo.css").read_text(encoding="utf-8")
CONFIG_TEXT = (ROOT / "backend" / "configure_demo.py").read_text(encoding="utf-8")
TREE = ast.parse(SOURCE_TEXT)


def load_core():
    wanted = {
        "BinanceDemoError", "signed_query", "decimal_text", "floor_step", "round_tick", "normalize_symbol",
        "response_rows", "validate_levels", "verify_leverage_response", "verify_symbol_configuration",
        "set_isolated_margin", "apply_verified_leverage", "position_mode", "ensure_one_way_position_mode",
        "update_position_lifecycle",
    }
    nodes = [node for node in TREE.body if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in wanted]
    future = ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)
    namespace = {
        "hashlib": hashlib,
        "hmac": hmac,
        "urlencode": urlencode,
        "Decimal": Decimal,
        "ROUND_DOWN": ROUND_DOWN,
        "ROUND_HALF_UP": ROUND_HALF_UP,
        "DEMO_REST_BASE": "https://demo-fapi.binance.com",
        "re": re,
        "Any": object,
    }
    module = ast.fix_missing_locations(ast.Module(body=[future, *nodes], type_ignores=[]))
    exec(compile(module, str(SOURCE_PATH), "exec"), namespace)
    return namespace


CORE = load_core()


class V203BinanceDemoSafetyTests(unittest.TestCase):
    def test_connector_is_hard_locked_to_official_demo_hosts(self):
        self.assertIn('DEMO_REST_BASE = "https://demo-fapi.binance.com"', SOURCE_TEXT)
        self.assertIn('DEMO_WS_BASE = "wss://demo-fstream.binance.com"', SOURCE_TEXT)
        self.assertNotIn('"https://fapi.binance.com"', SOURCE_TEXT)
        self.assertNotIn('"wss://fstream.binance.com"', SOURCE_TEXT)
        self.assertIn("real_trading_locked", SOURCE_TEXT)

    def test_hmac_signature_is_deterministic_and_matches_sha256(self):
        params = {"symbol": "ETHUSDT", "side": "BUY", "timestamp": 123456789, "recvWindow": 5000}
        query, signature = CORE["signed_query"]("demo-secret", params)
        expected_query = urlencode(list(params.items()))
        expected = hmac.new(b"demo-secret", expected_query.encode(), hashlib.sha256).hexdigest()
        self.assertEqual(query, expected_query)
        self.assertEqual(signature, expected)

    def test_quantity_and_price_rounding_never_inflate_quantity(self):
        floor_step = CORE["floor_step"]
        round_tick = CORE["round_tick"]
        self.assertEqual(floor_step(Decimal("1.239"), Decimal("0.01")), Decimal("1.23"))
        self.assertEqual(round_tick(Decimal("64.126"), Decimal("0.05")), Decimal("64.15"))

    def test_direction_levels_are_strictly_ordered(self):
        validate = CORE["validate_levels"]
        validate("LONG", Decimal("100"), Decimal("98"), [Decimal("102"), Decimal("104"), Decimal("106")])
        validate("SHORT", Decimal("100"), Decimal("102"), [Decimal("98"), Decimal("96"), Decimal("94")])
        with self.assertRaises(CORE["BinanceDemoError"]):
            validate("LONG", Decimal("100"), Decimal("101"), [Decimal("102"), Decimal("104"), Decimal("106")])

    def test_symbol_sanitizer_only_accepts_usdt_contracts(self):
        normalize = CORE["normalize_symbol"]
        self.assertEqual(normalize("eth/usdt"), "ETHUSDT")
        with self.assertRaises(CORE["BinanceDemoError"]):
            normalize("BTCUSD")

    def test_manual_arm_and_fixed_risk_caps_are_present(self):
        self.assertIn('MAX_MARGIN_USDT = Decimal("100")', SOURCE_TEXT)
        self.assertIn("MAX_LEVERAGE = 2", SOURCE_TEXT)
        self.assertIn("ARM_SECONDS = 10 * 60", SOURCE_TEXT)
        self.assertIn('body.confirmation.strip().upper() != "DEMO"', SOURCE_TEXT)
        self.assertIn("if not armed(state)", SOURCE_TEXT)
        self.assertIn("reduceOnly", SOURCE_TEXT)

    def test_leverage_and_isolated_margin_are_verified_before_entry(self):
        leverage = CORE["verify_leverage_response"](
            {"symbol": "BTCUSDT", "leverage": 2, "maxNotionalValue": "50000000"},
            "BTCUSDT",
            2,
        )
        self.assertTrue(leverage["leverage_verified"])
        self.assertEqual(leverage["applied_leverage"], 2)
        configuration = CORE["verify_symbol_configuration"](
            [{"symbol": "BTCUSDT", "marginType": "ISOLATED", "leverage": 2, "maxNotionalValue": "50000000"}],
            "BTCUSDT",
            2,
        )
        self.assertEqual(configuration["margin_type"], "isolated")
        with self.assertRaises(CORE["BinanceDemoError"]):
            CORE["verify_leverage_response"]({"symbol": "BTCUSDT", "leverage": 1}, "BTCUSDT", 2)
        with self.assertRaises(CORE["BinanceDemoError"]):
            CORE["verify_symbol_configuration"](
                [{"symbol": "BTCUSDT", "marginType": "CROSSED", "leverage": 2}], "BTCUSDT", 2,
            )

    def test_position_v3_missing_fields_are_never_invented_as_1x_cross(self):
        self.assertIn('("GET", "/fapi/v1/symbolConfig")', SOURCE_TEXT)
        self.assertIn('("POST", "/fapi/v1/marginType")', SOURCE_TEXT)
        self.assertIn('"marginType": "ISOLATED"', SOURCE_TEXT)
        self.assertNotIn('int(item.get("leverage", 1))', SOURCE_TEXT)
        self.assertNotIn('item.get("marginType", "cross")', SOURCE_TEXT)

    def test_entry_post_is_not_blindly_retried_on_unknown_status(self):
        self.assertIn("unknown_execution", SOURCE_TEXT)
        self.assertIn("find_order_by_client_id", SOURCE_TEXT)
        self.assertNotIn("for attempt in", SOURCE_TEXT)
        self.assertIn("origClientOrderId", SOURCE_TEXT)

    def test_position_lifecycle_tracks_partial_targets_and_full_close(self):
        lifecycle = CORE["update_position_lifecycle"]
        plan = {"position_id": "demo-123", "initial_quantity": "10", "quantity": "10"}
        lifecycle(plan, Decimal("10"))
        self.assertEqual(plan["position_status"], "OPEN")
        self.assertEqual(plan["remaining_quantity"], "10")
        lifecycle(plan, Decimal("7"))
        self.assertEqual(plan["tp1_status"], "FILLED")
        self.assertEqual(plan["position_id"], "demo-123")
        lifecycle(plan, Decimal("4"))
        self.assertEqual(plan["tp2_status"], "FILLED")
        lifecycle(plan, Decimal("0"))
        self.assertEqual(plan["position_status"], "CLOSED")
        self.assertEqual(plan["tp3_status"], "FILLED")

    def test_credentials_stay_server_side_and_out_of_user_interface(self):
        self.assertIn("getpass.getpass", CONFIG_TEXT)
        self.assertIn("PANODAN YAPIŞTIR", CONFIG_TEXT)
        self.assertIn("backend/.env", (ROOT / "V20-3-BINANCE-FUTURES-DEMO.md").read_text(encoding="utf-8"))
        self.assertNotIn("BINANCE_DEMO_SECRET_KEY", FRONTEND_TEXT)
        self.assertNotIn("secret_key", FRONTEND_TEXT.lower())
        self.assertIn("backend/.env", (ROOT / ".gitignore").read_text(encoding="utf-8"))

    def test_main_router_and_modern_demo_panel_are_integrated(self):
        self.assertIn("binance_demo_router", MAIN_TEXT)
        self.assertIn('version="25.0.0"', MAIN_TEXT)
        self.assertIn("Binance Futures Demo Komuta Merkezi", FRONTEND_TEXT)
        self.assertIn("demoLiveChart", FRONTEND_TEXT)
        self.assertIn("apiErrorMessage", FRONTEND_TEXT)
        self.assertIn("parsed <= 100", FRONTEND_TEXT)
        self.assertIn("Giriş, Stop, TP ve Seviye Haritası", FRONTEND_TEXT)
        self.assertIn("ACİL DEMO DURDUR", FRONTEND_TEXT)
        self.assertIn("KALDIRAÇ VE MARJİN DENETİMİ", FRONTEND_TEXT)
        self.assertIn("İstenen kaldıraç", FRONTEND_TEXT)
        self.assertIn("demoTicketFeedback", FRONTEND_TEXT)
        self.assertIn("await ensure_one_way_position_mode(client)", SOURCE_TEXT)
        self.assertIn("await ensure_one_way_position_mode(client)", ROOT_SOURCE_TEXT)
        self.assertIn(".demoPositionMap", STYLE_TEXT)
        self.assertIn(".appShell.view-v20-demo>.binanceDemoDeck", STYLE_TEXT)


class V203BinanceDemoAsyncSafetyTests(unittest.IsolatedAsyncioTestCase):
    async def test_one_way_mode_cleans_demo_orders_before_mode_change(self):
        class FakeClient:
            def __init__(self):
                self.calls = []
                self.hedge = True
                self.orders = [{"symbol": "BTCUSDT", "orderId": 11}]
                self.algo_orders = [{"symbol": "ETHUSDT", "algoId": 22}]

            async def signed(self, method, path, params=None):
                self.calls.append((method, path, params or {}))
                if path == "/fapi/v1/positionSide/dual" and method == "GET":
                    return {"dualSidePosition": self.hedge}
                if path == "/fapi/v1/openOrders":
                    return list(self.orders)
                if path == "/fapi/v1/openAlgoOrders":
                    return list(self.algo_orders)
                if path == "/fapi/v1/order" and method == "DELETE":
                    self.orders.clear()
                    return {"orderId": 11, "status": "CANCELED"}
                if path == "/fapi/v1/algoOrder" and method == "DELETE":
                    self.algo_orders.clear()
                    return {"algoId": 22, "algoStatus": "CANCELED"}
                if path == "/fapi/v1/positionSide/dual" and method == "POST":
                    self.hedge = False
                    return {"dualSidePosition": False}
                raise AssertionError((method, path, params))

        client = FakeClient()
        self.assertEqual(await CORE["ensure_one_way_position_mode"](client), 2)
        self.assertEqual([call[1] for call in client.calls], [
            "/fapi/v1/positionSide/dual", "/fapi/v1/openOrders", "/fapi/v1/openAlgoOrders",
            "/fapi/v1/order", "/fapi/v1/algoOrder", "/fapi/v1/openOrders",
            "/fapi/v1/openAlgoOrders", "/fapi/v1/positionSide/dual", "/fapi/v1/positionSide/dual",
        ])

    async def test_one_way_mode_is_noop_when_already_one_way(self):
        class FakeClient:
            async def signed(self, method, path, params=None):
                self.calls = getattr(self, "calls", 0) + 1
                return {"dualSidePosition": False}

        client = FakeClient()
        self.assertEqual(await CORE["ensure_one_way_position_mode"](client), 0)
        self.assertEqual(client.calls, 1)

    async def test_one_way_mode_rechecks_orders_after_binance_4067(self):
        class FakeClient:
            def __init__(self):
                self.hedge = True
                self.mode_attempts = 0
                self.orders = [{"symbol": "BTCUSDT", "orderId": 11}]

            async def signed(self, method, path, params=None):
                if path == "/fapi/v1/positionSide/dual" and method == "GET":
                    return {"dualSidePosition": self.hedge}
                if path == "/fapi/v1/openOrders":
                    return list(self.orders)
                if path == "/fapi/v1/openAlgoOrders":
                    return []
                if path == "/fapi/v1/order" and method == "DELETE":
                    self.orders.clear()
                    return {"orderId": 11, "status": "CANCELED"}
                if path == "/fapi/v1/positionSide/dual" and method == "POST":
                    self.mode_attempts += 1
                    if self.mode_attempts == 1:
                        raise CORE["BinanceDemoError"]("open orders", exchange_code=-4067)
                    self.hedge = False
                    return {"dualSidePosition": False}
                raise AssertionError((method, path, params))

        client = FakeClient()
        self.assertEqual(await CORE["ensure_one_way_position_mode"](client), 1)
        self.assertEqual(client.mode_attempts, 2)

    async def test_isolated_margin_then_exact_leverage_and_symbol_config_are_required(self):
        class FakeClient:
            def __init__(self):
                self.calls = []

            async def signed(self, method, path, params=None):
                self.calls.append((method, path, params or {}))
                if path == "/fapi/v1/marginType":
                    return {"code": 200, "msg": "success"}
                if path == "/fapi/v1/leverage":
                    return {"symbol": "BTCUSDT", "leverage": 2, "maxNotionalValue": "50000000"}
                if path == "/fapi/v1/symbolConfig":
                    return [{"symbol": "BTCUSDT", "marginType": "ISOLATED", "leverage": 2}]
                raise AssertionError(path)

        client = FakeClient()
        await CORE["set_isolated_margin"](client, "BTCUSDT")
        audit = await CORE["apply_verified_leverage"](client, "BTCUSDT", 2)
        self.assertEqual(audit["applied_leverage"], 2)
        self.assertEqual(audit["margin_type"], "isolated")
        self.assertEqual([call[1] for call in client.calls], [
            "/fapi/v1/marginType", "/fapi/v1/leverage", "/fapi/v1/symbolConfig",
        ])

    async def test_already_isolated_exchange_code_is_safe_and_other_errors_fail(self):
        class FakeClient:
            def __init__(self, code):
                self.code = code

            async def signed(self, method, path, params=None):
                raise CORE["BinanceDemoError"]("margin response", exchange_code=self.code)

        await CORE["set_isolated_margin"](FakeClient(-4046), "BTCUSDT")
        with self.assertRaises(CORE["BinanceDemoError"]):
            await CORE["set_isolated_margin"](FakeClient(-4047), "BTCUSDT")


if __name__ == "__main__":
    unittest.main(verbosity=2)
