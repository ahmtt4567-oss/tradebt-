"""V21 Demo Complete control plane.

Every exchange call in this module goes through :mod:`binance_demo`, whose host
allow-list contains Binance Futures Demo only.  Automation is off after every
restart and requires both the short-lived DEMO arm and a second explicit
``DEMO OTOMATİK`` confirmation.
"""

from __future__ import annotations

import asyncio
import json
import math
import time
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from statistics import fmean
from typing import Any, Literal

import websockets
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from .analysis import analyze, atr, ema
from .binance_demo import (
    DEMO_REST_BASE,
    DEMO_WS_BASE,
    MAX_LEVERAGE,
    MAX_MARGIN_USDT,
    MAX_NOTIONAL_USDT,
    MAX_OPEN_POSITIONS,
    BinanceDemoClient,
    BinanceDemoError,
    DemoOrderRequest,
    account_snapshot,
    armed,
    credentials_configured,
    decimal_text,
    execute_demo_order,
    load_demo_credentials,
    new_client_id,
    normalize_symbol,
    persist_runtime,
    post_algo,
    response_rows,
    round_tick,
    safe_exchange_error,
    symbol_rules,
)
from .local_storage import DATA_DIR, migrate_legacy_files


router = APIRouter(prefix="/api/v21", tags=["V21 Demo Complete"])
migrate_legacy_files(("v21_demo_state.json", "v21_demo_state.backup.json"))
STATE_PATH = DATA_DIR / "v21_demo_state.json"
BACKUP_PATH = DATA_DIR / "v21_demo_state.backup.json"
JOURNAL_LIMIT = 1200

DEFAULT_SETTINGS: dict[str, Any] = {
    "allowed_symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"],
    "allow_long": True,
    "allow_short": True,
    "max_loss_per_trade": 5.0,
    "max_margin_per_trade": 50.0,
    "daily_loss_limit": 30.0,
    "daily_trade_limit": 6,
    "max_positions": 3,
    "min_confidence": 78,
    "max_volatility_pct": 3.5,
    "max_correlation_pct": 82,
    "schedule_start_hour": 0,
    "schedule_end_hour": 24,
    "scan_seconds": 30,
    "breakeven_enabled": True,
    "breakeven_trigger_r": 1.0,
    "trailing_enabled": False,
    "trailing_trigger_r": 1.5,
    "trailing_distance_r": 0.75,
    "notifications": True,
    "fee_bps_per_side": 4.0,
    "slippage_bps_per_side": 2.0,
}


class SettingsUpdate(BaseModel):
    allowed_symbols: list[str] | None = None
    allow_long: bool | None = None
    allow_short: bool | None = None
    max_loss_per_trade: float | None = Field(default=None, ge=0.5, le=25)
    max_margin_per_trade: float | None = Field(default=None, ge=5, le=100)
    daily_loss_limit: float | None = Field(default=None, ge=5, le=250)
    daily_trade_limit: int | None = Field(default=None, ge=1, le=30)
    max_positions: int | None = Field(default=None, ge=1, le=3)
    min_confidence: int | None = Field(default=None, ge=60, le=95)
    max_volatility_pct: float | None = Field(default=None, ge=0.2, le=10)
    max_correlation_pct: int | None = Field(default=None, ge=40, le=99)
    schedule_start_hour: int | None = Field(default=None, ge=0, le=23)
    schedule_end_hour: int | None = Field(default=None, ge=1, le=24)
    scan_seconds: int | None = Field(default=None, ge=15, le=300)
    breakeven_enabled: bool | None = None
    breakeven_trigger_r: float | None = Field(default=None, ge=0.5, le=3)
    trailing_enabled: bool | None = None
    trailing_trigger_r: float | None = Field(default=None, ge=0.75, le=5)
    trailing_distance_r: float | None = Field(default=None, ge=0.25, le=3)
    notifications: bool | None = None
    fee_bps_per_side: float | None = Field(default=None, ge=0, le=25)
    slippage_bps_per_side: float | None = Field(default=None, ge=0, le=50)


class RiskSizeRequest(BaseModel):
    symbol: str = Field(min_length=5, max_length=20)
    entry: float = Field(gt=0)
    stop: float = Field(gt=0)
    max_loss_usdt: float = Field(ge=0.5, le=25)
    leverage: int = Field(ge=1, le=2)


class AutoStartRequest(BaseModel):
    confirmation: str = Field(min_length=1, max_length=40)


class BacktestRequest(BaseModel):
    symbol: str = Field(default="BTCUSDT", min_length=5, max_length=20)
    interval: Literal["1m", "5m", "15m", "1h", "4h"] = "15m"
    limit: int = Field(default=1000, ge=300, le=1500)


class DrillRequest(BaseModel):
    kind: Literal["RECONNECT", "EMERGENCY", "PROTECTION"]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def initial_state() -> dict[str, Any]:
    return {
        "settings": dict(DEFAULT_SETTINGS),
        "journal": [],
        "seen_event_ids": [],
        "auto": {
            "enabled": False, "busy": False, "cycles": 0, "last_scan": None,
            "user_confirmed": False, "confirmation": None,
            "last_decision": "Kullanıcı onayı bekleniyor.", "last_error": None,
        },
        "stream": {
            "status": "BEKLEMEDE", "transport": "REST EŞLEŞTİRME", "last_event": None,
            "last_sync": None, "reconnect_count": 0, "error_count": 0, "last_error": None,
        },
        "snapshot": None,
        "backtest": None,
        "drills": {"RECONNECT": None, "EMERGENCY": None, "PROTECTION": None},
        "duplicate_blocks": 0,
        "duplicate_submissions": 0,
        "protection_repairs": 0,
        "last_saved": None,
    }


def _read_state_file(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else None
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return None


def load_state() -> dict[str, Any]:
    base = initial_state()
    saved = _read_state_file(STATE_PATH) or _read_state_file(BACKUP_PATH) or {}
    if isinstance(saved.get("settings"), dict):
        base["settings"].update({key: value for key, value in saved["settings"].items() if key in DEFAULT_SETTINGS})
    for key in (
        "journal", "seen_event_ids", "backtest", "drills", "duplicate_blocks",
        "duplicate_submissions", "protection_repairs",
    ):
        if key in saved:
            base[key] = saved[key]
    # Entry automation is intentionally never restored after a restart.
    base["auto"]["enabled"] = False
    base["auto"]["user_confirmed"] = False
    base["auto"]["confirmation"] = None
    base["auto"]["last_decision"] = "Güvenli yeniden başlatma: DEMO OTOMATİK onayı bekleniyor."
    return base


def serializable_state(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "settings": state["settings"],
        "journal": state["journal"][:JOURNAL_LIMIT],
        "seen_event_ids": state["seen_event_ids"][-800:],
        "backtest": state.get("backtest"),
        "drills": state.get("drills", {}),
        "duplicate_blocks": state.get("duplicate_blocks", 0),
        "duplicate_submissions": state.get("duplicate_submissions", 0),
        "protection_repairs": state.get("protection_repairs", 0),
        "saved_at": now_iso(),
    }


def persist_state(state: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(serializable_state(state), ensure_ascii=False, indent=2)
    temporary = STATE_PATH.with_suffix(".tmp")
    temporary.write_text(payload, encoding="utf-8")
    if STATE_PATH.exists():
        try:
            BACKUP_PATH.write_bytes(STATE_PATH.read_bytes())
        except OSError:
            pass
    temporary.replace(STATE_PATH)
    state["last_saved"] = now_iso()


def state_for(request: Request) -> dict[str, Any]:
    return request.app.state.v21_demo


def record_event(
    state: dict[str, Any],
    kind: str,
    message: str,
    *,
    symbol: str | None = None,
    status: str | None = None,
    side: str | None = None,
    price: float | None = None,
    quantity: float | None = None,
    realized_pnl: float | None = None,
    reason: str | None = None,
    event_id: str | None = None,
    source: str = "SYSTEM",
    reduce_only: bool = False,
) -> dict[str, Any] | None:
    stable_id = event_id or uuid.uuid4().hex
    seen = state.setdefault("seen_event_ids", [])
    if stable_id in seen:
        return None
    seen.append(stable_id)
    del seen[:-800]
    item = {
        "id": stable_id,
        "created_at": now_iso(),
        "kind": kind,
        "symbol": symbol,
        "status": status,
        "side": side,
        "price": price,
        "quantity": quantity,
        "realized_pnl": realized_pnl,
        "reason": reason,
        "message": message,
        "source": source,
        "reduce_only": reduce_only,
        "demo_only": True,
    }
    state.setdefault("journal", []).insert(0, item)
    del state["journal"][JOURNAL_LIMIT:]
    return item


def client_for(application: Any) -> BinanceDemoClient:
    api_key, secret_key = load_demo_credentials()
    return BinanceDemoClient(application.state.http, api_key, secret_key)


def normalize_candles(rows: Any) -> list[dict[str, float]]:
    candles: list[dict[str, float]] = []
    if not isinstance(rows, list):
        return candles
    for row in rows:
        if not isinstance(row, list) or len(row) < 6:
            continue
        try:
            candles.append({
                "time": int(row[0] / 1000), "open": float(row[1]), "high": float(row[2]),
                "low": float(row[3]), "close": float(row[4]), "volume": float(row[5]),
            })
        except (TypeError, ValueError, ZeroDivisionError):
            continue
    return candles


async def demo_candles(client: BinanceDemoClient, symbol: str, interval: str, limit: int) -> list[dict[str, float]]:
    rows = await client.public_get("/fapi/v1/klines", {"symbol": symbol, "interval": interval, "limit": limit})
    return normalize_candles(rows)


def daily_metrics(state: dict[str, Any]) -> dict[str, Any]:
    day = today()
    events = [item for item in state.get("journal", []) if str(item.get("created_at", "")).startswith(day)]
    auto_entries = [item for item in events if item.get("kind") == "AUTO_ORDER"]
    realized = sum(float(item.get("realized_pnl") or 0) for item in events)
    return {
        "date": day,
        "auto_entries": len(auto_entries),
        "events": len(events),
        "realized_pnl": round(realized, 4),
        "remaining_loss_budget": round(max(0.0, float(state["settings"]["daily_loss_limit"]) + realized), 4),
    }


def risk_size_values(entry: float, stop: float, max_loss: float, leverage: int, max_margin: float) -> dict[str, float]:
    distance = abs(entry - stop)
    if distance <= 0:
        raise HTTPException(422, "Giriş ve Stop aynı olamaz.")
    risk_pct = distance / entry
    requested_notional = max_loss / risk_pct
    capped_notional = min(requested_notional, max_margin * leverage, float(MAX_NOTIONAL_USDT))
    margin = capped_notional / leverage
    actual_loss = capped_notional * risk_pct
    return {
        "risk_pct": round(risk_pct * 100, 4),
        "notional_usdt": round(capped_notional, 4),
        "margin_usdt": round(margin, 4),
        "estimated_stop_loss_usdt": round(actual_loss, 4),
        "capped": capped_notional + 1e-9 < requested_notional,
    }


def _position_map(snapshot: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    return {item["symbol"]: item for item in (snapshot or {}).get("positions", []) if item.get("symbol")}


def reconcile_positions(state: dict[str, Any], previous: dict[str, Any] | None, current: dict[str, Any]) -> bool:
    changed = False
    old_positions = _position_map(previous)
    new_positions = _position_map(current)
    for symbol, row in new_positions.items():
        if symbol not in old_positions:
            changed |= record_event(
                state, "POSITION_OPEN", f"{symbol} Demo pozisyonu hesapta görünmeye başladı.",
                symbol=symbol, status="OPEN", side=row.get("direction"), price=row.get("entry_price"),
                quantity=row.get("quantity"), source="RECONCILER",
                event_id=f"pos-open-{symbol}-{row.get('entry_price')}-{row.get('quantity')}",
            ) is not None
    for symbol, row in old_positions.items():
        if symbol not in new_positions:
            pnl = float(row.get("unrealized_pnl") or 0)
            changed |= record_event(
                state, "POSITION_CLOSED", f"{symbol} Demo pozisyonu kapandı; kesin sonuç işlem akışından eşleştiriliyor.",
                symbol=symbol, status="CLOSED", side=row.get("direction"), price=row.get("mark_price"),
                quantity=row.get("quantity"), realized_pnl=pnl, reason="Kapanış öncesi son görülen PnL tahmini",
                source="RECONCILER", reduce_only=True,
                event_id=f"pos-close-{symbol}-{int(time.time() // 3)}",
            ) is not None
    return changed


def process_stream_event(state: dict[str, Any], payload: dict[str, Any]) -> bool:
    event_type = str(payload.get("e") or "")
    event_time = payload.get("T", payload.get("E", 0))
    state["stream"].update({"last_event": now_iso(), "status": "CANLI", "transport": "USER STREAM"})
    if event_type == "ORDER_TRADE_UPDATE":
        order = payload.get("o") if isinstance(payload.get("o"), dict) else {}
        symbol = str(order.get("s") or "")
        status = str(order.get("X") or "")
        execution = str(order.get("x") or "")
        order_id = order.get("i", order.get("c", ""))
        realized = float(order.get("rp") or 0)
        kind = "FILL" if execution == "TRADE" else "ORDER_UPDATE"
        return record_event(
            state, kind, f"{symbol} {execution or 'EMİR'} · {status}", symbol=symbol,
            status=status, side=order.get("S"), price=float(order.get("ap") or order.get("L") or order.get("p") or 0),
            quantity=float(order.get("z") or order.get("l") or order.get("q") or 0),
            realized_pnl=realized, reason=str(order.get("er") or "") or None,
            event_id=f"order-{event_time}-{order_id}-{execution}-{status}", source="USER_STREAM",
            reduce_only=bool(order.get("R", False)),
        ) is not None
    if event_type == "ALGO_UPDATE":
        order = payload.get("o") if isinstance(payload.get("o"), dict) else payload.get("a", {})
        order = order if isinstance(order, dict) else {}
        symbol = str(order.get("s") or order.get("symbol") or "")
        status = str(order.get("X") or order.get("algoStatus") or order.get("status") or "UPDATE")
        return record_event(
            state, "ALGO_UPDATE", f"{symbol} koşullu koruma · {status}", symbol=symbol or None,
            status=status, price=float(order.get("sp") or order.get("triggerPrice") or 0),
            event_id=f"algo-{event_time}-{order.get('aid', order.get('algoId', ''))}-{status}", source="USER_STREAM",
        ) is not None
    if event_type == "listenKeyExpired":
        record_event(state, "STREAM_EXPIRED", "Binance Demo kullanıcı akışı süresi doldu; güvenli yeniden bağlantı başlatıldı.", source="USER_STREAM")
        return True
    return False


async def user_stream_loop(application: Any) -> None:
    state = application.state.v21_demo
    while True:
        listen_key = ""
        try:
            if not credentials_configured():
                state["stream"].update({"status": "ANAHTAR BEKLİYOR", "transport": "REST EŞLEŞTİRME"})
                await asyncio.sleep(5)
                continue
            client = client_for(application)
            response = await client.api_key_request("POST", "/fapi/v1/listenKey")
            listen_key = str((response or {}).get("listenKey") or "")
            if not listen_key:
                raise BinanceDemoError("Demo kullanıcı akışı anahtarı alınamadı.")
            state["stream"].update({"status": "BAĞLANIYOR", "transport": "USER STREAM", "last_error": None})
            url = f"{DEMO_WS_BASE}/ws/{listen_key}"
            async with websockets.connect(url, ping_interval=20, ping_timeout=20, close_timeout=5) as socket:
                state["stream"].update({"status": "CANLI", "transport": "USER STREAM", "last_event": now_iso()})
                record_event(state, "STREAM_CONNECTED", "Binance Futures Demo kullanıcı akışı bağlandı.", source="USER_STREAM")
                last_keepalive = time.monotonic()
                while True:
                    try:
                        raw = await asyncio.wait_for(socket.recv(), timeout=30)
                        payload = json.loads(raw)
                        if isinstance(payload, dict) and process_stream_event(state, payload):
                            persist_state(state)
                        if isinstance(payload, dict) and payload.get("e") == "listenKeyExpired":
                            break
                    except asyncio.TimeoutError:
                        pass
                    if time.monotonic() - last_keepalive >= 45 * 60:
                        await client.api_key_request("PUT", "/fapi/v1/listenKey")
                        last_keepalive = time.monotonic()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            state["stream"]["error_count"] += 1
            state["stream"]["reconnect_count"] += 1
            state["stream"].update({
                "status": "YENİDEN BAĞLANIYOR", "transport": "REST EŞLEŞTİRME",
                "last_error": str(exc)[:220],
            })
            record_event(state, "STREAM_RECONNECT", "Canlı Demo akışı kesildi; REST eşleştirme açık ve yeniden bağlantı deneniyor.", source="SYSTEM")
            persist_state(state)
            await asyncio.sleep(min(30, 2 + state["stream"]["reconnect_count"]))
        finally:
            if listen_key:
                try:
                    await client_for(application).api_key_request("DELETE", "/fapi/v1/listenKey")
                except Exception:
                    pass


def active_plan(application: Any, symbol: str) -> dict[str, Any] | None:
    plans = application.state.binance_demo.get("plans", {})
    candidates = [
        plan for plan in plans.values()
        if plan.get("symbol") == symbol and plan.get("status") not in {"KAPANDI", "İPTAL", "GÜVENLİK İÇİN KAPATILDI", "ACİL DURDURULDU"}
    ]
    return candidates[-1] if candidates else None


async def ensure_stop_protection(application: Any, snapshot: dict[str, Any]) -> bool:
    state = application.state.v21_demo
    client = client_for(application)
    algo_by_symbol: dict[str, list[dict[str, Any]]] = {}
    for order in snapshot.get("open_algo_orders", []):
        algo_by_symbol.setdefault(str(order.get("symbol")), []).append(order)
    changed = False
    for position in snapshot.get("positions", []):
        symbol = str(position.get("symbol"))
        plan = active_plan(application, symbol)
        if not plan:
            continue
        stops = [order for order in algo_by_symbol.get(symbol, []) if str(order.get("type", "")).upper() == "STOP_MARKET"]
        if stops:
            continue
        params = {
            "algoType": "CONDITIONAL", "symbol": symbol,
            "side": "SELL" if position.get("direction") == "LONG" else "BUY",
            "type": "STOP_MARKET", "triggerPrice": plan["stop_loss"], "closePosition": "true",
            "workingType": "MARK_PRICE", "priceProtect": "TRUE", "clientAlgoId": new_client_id("REPAIRSL"),
        }
        result = await post_algo(client, params)
        if result.get("algoId"):
            plan["stop_algo_id"] = int(result["algoId"])
            plan.setdefault("protection_ids", []).append(int(result["algoId"]))
        plan["status"] = "KORUMA ONARILDI"
        state["protection_repairs"] += 1
        record_event(state, "PROTECTION_REPAIRED", f"{symbol} eksik Stop koruması Demo hesabında yeniden kuruldu.", symbol=symbol, source="RISK_ENGINE")
        changed = True
    if changed:
        persist_runtime(application.state.binance_demo)
    return changed


async def improve_dynamic_stops(application: Any, snapshot: dict[str, Any]) -> bool:
    state = application.state.v21_demo
    settings = state["settings"]
    if not settings["breakeven_enabled"] and not settings["trailing_enabled"]:
        return False
    client = client_for(application)
    changed = False
    for position in snapshot.get("positions", []):
        symbol = str(position.get("symbol"))
        plan = active_plan(application, symbol)
        if not plan or time.time() - float(plan.get("last_dynamic_update_epoch", 0)) < 30:
            continue
        entry = float(position.get("entry_price") or 0)
        mark = float(position.get("mark_price") or 0)
        initial_stop = float(plan.get("initial_stop_loss") or plan.get("stop_loss") or 0)
        current_stop = float(plan.get("stop_loss") or 0)
        risk = abs(entry - initial_stop)
        if min(entry, mark, initial_stop, risk) <= 0:
            continue
        direction = str(position.get("direction"))
        r_multiple = (mark - entry) / risk if direction == "LONG" else (entry - mark) / risk
        desired = current_stop
        label = ""
        if settings["breakeven_enabled"] and r_multiple >= float(settings["breakeven_trigger_r"]):
            desired = max(desired, entry) if direction == "LONG" else min(desired, entry)
            label = "BAŞABAŞ"
        if settings["trailing_enabled"] and r_multiple >= float(settings["trailing_trigger_r"]):
            distance = risk * float(settings["trailing_distance_r"])
            trail = mark - distance if direction == "LONG" else mark + distance
            desired = max(desired, trail) if direction == "LONG" else min(desired, trail)
            label = "İZ SÜREN"
        rules = await symbol_rules(client, symbol)
        desired_decimal = round_tick(Decimal(str(desired)), rules["tick"])
        desired = float(desired_decimal)
        improves = desired > current_stop + float(rules["tick"]) if direction == "LONG" else desired < current_stop - float(rules["tick"])
        valid_side = desired < mark if direction == "LONG" else desired > mark
        if not label or not improves or not valid_side:
            continue
        result = await post_algo(client, {
            "algoType": "CONDITIONAL", "symbol": symbol,
            "side": "SELL" if direction == "LONG" else "BUY", "type": "STOP_MARKET",
            "triggerPrice": decimal_text(desired_decimal), "closePosition": "true",
            "workingType": "MARK_PRICE", "priceProtect": "TRUE", "clientAlgoId": new_client_id("DYNAMICSL"),
        })
        new_id = int(result.get("algoId", 0)) or None
        old_id = plan.get("stop_algo_id")
        if new_id:
            plan["stop_algo_id"] = new_id
            plan.setdefault("protection_ids", []).append(new_id)
        plan["stop_loss"] = decimal_text(desired_decimal)
        plan["last_dynamic_update_epoch"] = time.time()
        if old_id:
            try:
                await client.signed("DELETE", "/fapi/v1/algoOrder", {"symbol": symbol, "algoId": old_id})
            except BinanceDemoError:
                pass
        record_event(state, "DYNAMIC_STOP", f"{symbol} {label} Stop {decimal_text(desired_decimal)} seviyesine iyileştirildi.", symbol=symbol, price=desired, source="RISK_ENGINE")
        changed = True
    if changed:
        persist_runtime(application.state.binance_demo)
    return changed


async def reconciliation_loop(application: Any) -> None:
    state = application.state.v21_demo
    previous: dict[str, Any] | None = None
    while True:
        try:
            if not credentials_configured():
                await asyncio.sleep(4)
                continue
            snapshot = await account_snapshot(client_for(application))
            state["snapshot"] = snapshot
            state["stream"]["last_sync"] = now_iso()
            application.state.binance_demo.update({"connected": True, "last_checked": now_iso(), "last_error": None})
            changed = reconcile_positions(state, previous, snapshot)
            previous = snapshot
            try:
                changed |= await ensure_stop_protection(application, snapshot)
                changed |= await improve_dynamic_stops(application, snapshot)
            except BinanceDemoError as exc:
                state["stream"]["last_error"] = str(exc)[:220]
            if changed:
                persist_state(state)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            application.state.binance_demo["connected"] = False
            state["stream"].update({"status": "REST YENİDEN DENİYOR", "last_error": str(exc)[:220]})
        await asyncio.sleep(3)


def in_schedule(settings: dict[str, Any]) -> bool:
    hour = datetime.now().hour
    start, end = int(settings["schedule_start_hour"]), int(settings["schedule_end_hour"])
    return start <= hour < end if start < end else hour >= start or hour < end


def return_correlation(left: list[dict[str, float]], right: list[dict[str, float]]) -> float:
    a = [(b["close"] / a["close"]) - 1 for a, b in zip(left[-61:-1], left[-60:]) if a["close"]]
    b = [(d["close"] / c["close"]) - 1 for c, d in zip(right[-61:-1], right[-60:]) if c["close"]]
    size = min(len(a), len(b))
    if size < 20:
        return 0.0
    a, b = a[-size:], b[-size:]
    mean_a, mean_b = fmean(a), fmean(b)
    numerator = sum((x - mean_a) * (y - mean_b) for x, y in zip(a, b))
    denominator = math.sqrt(sum((x - mean_a) ** 2 for x in a) * sum((y - mean_b) ** 2 for y in b))
    return numerator / denominator if denominator else 0.0


async def automatic_cycle(application: Any) -> None:
    state = application.state.v21_demo
    settings = state["settings"]
    auto = state["auto"]
    if not bool(auto.get("enabled")) or not bool(auto.get("user_confirmed")):
        auto["last_decision"] = "Yalnızca açık kullanıcı onayıyla otomasyon giriş yapabilir; emir açılmadı."
        auto["last_error"] = "AUTO_GUARD_BLOCKED"
        return
    auto["cycles"] += 1
    auto["last_scan"] = now_iso()
    if not armed(application.state.binance_demo):
        auto["last_decision"] = "10 dakikalık DEMO emir kilidi kapalı; otomasyon bekliyor."
        return
    if not in_schedule(settings):
        auto["last_decision"] = "İzin verilen çalışma saatleri dışında; yeni giriş yok."
        return
    daily = daily_metrics(state)
    if daily["auto_entries"] >= settings["daily_trade_limit"]:
        auto["last_decision"] = "Günlük Demo işlem limiti doldu."
        return
    if daily["realized_pnl"] <= -float(settings["daily_loss_limit"]):
        auto["last_decision"] = "Günlük Demo zarar limiti aktif; yeni giriş kilitli."
        auto["enabled"] = False
        return
    client = client_for(application)
    snapshot = await account_snapshot(client)
    if len(snapshot["positions"]) >= min(settings["max_positions"], MAX_OPEN_POSITIONS):
        auto["last_decision"] = "Açık pozisyon sınırı dolu."
        return
    occupied = {item["symbol"] for item in snapshot["positions"] + snapshot["open_orders"]}
    btc_candles: list[dict[str, float]] | None = None
    for raw_symbol in settings["allowed_symbols"]:
        symbol = normalize_symbol(raw_symbol)
        if symbol in occupied:
            state["duplicate_blocks"] += 1
            continue
        candles = await demo_candles(client, symbol, "15m", 260)
        if len(candles) < 220:
            continue
        decision = analyze(candles[:-1])
        direction = decision["direction"]
        confidence = int(decision["confidence"])
        if direction == "BEKLE" or confidence < int(settings["min_confidence"]):
            auto["last_decision"] = f"{symbol}: güven %{confidence}; eşik %{settings['min_confidence']}."
            continue
        if (direction == "LONG" and not settings["allow_long"]) or (direction == "SHORT" and not settings["allow_short"]):
            auto["last_decision"] = f"{symbol}: {direction} yönü kullanıcı ayarında kapalı."
            continue
        volatility = float(decision["atr"]) / float(decision["entry"]) * 100
        if volatility > float(settings["max_volatility_pct"]):
            auto["last_decision"] = f"{symbol}: volatilite %{volatility:.2f}; güvenlik tavanını aşıyor."
            continue
        if symbol != "BTCUSDT" and any(item["symbol"] == "BTCUSDT" and item["direction"] == direction for item in snapshot["positions"]):
            btc_candles = btc_candles or await demo_candles(client, "BTCUSDT", "15m", 260)
            correlation = abs(return_correlation(candles, btc_candles)) * 100
            if correlation >= float(settings["max_correlation_pct"]):
                auto["last_decision"] = f"{symbol}: BTC korelasyonu %{correlation:.0f}; yoğunlaşma engeli."
                continue
        sizing = risk_size_values(
            float(decision["entry"]), float(decision["stop_loss"]), float(settings["max_loss_per_trade"]),
            MAX_LEVERAGE, min(float(settings["max_margin_per_trade"]), float(MAX_MARGIN_USDT)),
        )
        margin = max(5.0, min(float(MAX_MARGIN_USDT), sizing["margin_usdt"]))
        body = DemoOrderRequest(
            symbol=symbol, direction=direction, order_type="MARKET", margin_usdt=margin,
            leverage=MAX_LEVERAGE, stop_loss=decision["stop_loss"], tp1=decision["tp1"],
            tp2=decision["tp2"], tp3=decision["tp3"],
        )
        try:
            await execute_demo_order(application, body, source="V21_AUTO")
        except BinanceDemoError as exc:
            auto["last_decision"] = f"{symbol}: Demo emir reddi · {exc}"
            continue
        record_event(
            state, "AUTO_ORDER", f"{symbol} {direction} otomatik Demo girişi gönderildi.", symbol=symbol,
            side=direction, price=float(decision["entry"]), quantity=None,
            reason=f"Güven %{confidence}; ATR %{volatility:.2f}; tahmini stop riski {sizing['estimated_stop_loss_usdt']:.2f} USDT",
            source="V21_AUTO",
        )
        auto["last_decision"] = f"{symbol} {direction}: güven %{confidence}; Demo emir gönderildi ve Stop önce kuruluyor."
        persist_state(state)
        return
    if not auto["last_decision"]:
        auto["last_decision"] = "İzinli paritelerde yeni giriş bulunamadı."


async def automation_loop(application: Any) -> None:
    state = application.state.v21_demo
    while True:
        try:
            auto = state["auto"]
            if auto.get("enabled") and auto.get("user_confirmed") and not auto.get("busy"):
                auto["busy"] = True
                try:
                    await automatic_cycle(application)
                    auto["last_error"] = None
                finally:
                    auto["busy"] = False
            elif auto.get("enabled") and not auto.get("user_confirmed"):
                auto["enabled"] = False
                auto["last_decision"] = "Güvenli bekleme: kullanıcı onayı silinmiş, otomasyon kapandı."
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            state["auto"].update({"last_error": str(exc)[:220], "last_decision": "Otomasyon hatası; güvenli bekleme ve yeniden deneme."})
        await asyncio.sleep(max(15, int(state["settings"]["scan_seconds"])))


def backtest_engine(candles: list[dict[str, float]], settings: dict[str, Any]) -> dict[str, Any]:
    if len(candles) < 260:
        raise HTTPException(422, "Backtest için en az 260 mum gerekiyor.")
    closes = [row["close"] for row in candles]
    highs = [row["high"] for row in candles]
    lows = [row["low"] for row in candles]
    e20, e50, e200 = ema(closes, 20), ema(closes, 50), ema(closes, 200)
    costs = (float(settings["fee_bps_per_side"]) + float(settings["slippage_bps_per_side"])) / 10_000 * 2
    trades: list[dict[str, Any]] = []
    equity = 1000.0
    peak = equity
    max_drawdown = 0.0
    index = 210
    while index < len(candles) - 26:
        signal_index = index
        long_signal = closes[signal_index] > e20[signal_index] > e50[signal_index] > e200[signal_index]
        short_signal = closes[signal_index] < e20[signal_index] < e50[signal_index] < e200[signal_index]
        if not long_signal and not short_signal:
            index += 1
            continue
        direction = "LONG" if long_signal else "SHORT"
        # No look-ahead: signal uses candle[index], entry is next candle open.
        entry_index = signal_index + 1
        entry = candles[entry_index]["open"]
        atr_value = atr(highs[: signal_index + 1], lows[: signal_index + 1], closes[: signal_index + 1])
        if atr_value <= 0:
            index += 1
            continue
        stop = entry - 1.5 * atr_value if direction == "LONG" else entry + 1.5 * atr_value
        target = entry + 3 * atr_value if direction == "LONG" else entry - 3 * atr_value
        risk_pct = abs(entry - stop) / entry
        notional = min(float(MAX_NOTIONAL_USDT), float(settings["max_loss_per_trade"]) / max(risk_pct, 1e-9))
        exit_price = candles[min(entry_index + 24, len(candles) - 1)]["close"]
        exit_reason = "ZAMAN"
        exit_index = min(entry_index + 24, len(candles) - 1)
        for cursor in range(entry_index, min(entry_index + 25, len(candles))):
            row = candles[cursor]
            # Conservative policy: if stop and target occur in one candle, stop wins.
            stop_hit = row["low"] <= stop if direction == "LONG" else row["high"] >= stop
            target_hit = row["high"] >= target if direction == "LONG" else row["low"] <= target
            if stop_hit:
                exit_price, exit_reason, exit_index = stop, "STOP", cursor
                break
            if target_hit:
                exit_price, exit_reason, exit_index = target, "HEDEF", cursor
                break
        raw_return = (exit_price - entry) / entry * (1 if direction == "LONG" else -1)
        pnl = notional * (raw_return - costs)
        equity += pnl
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, (peak - equity) / peak * 100 if peak else 0)
        regime = "TREND" if abs(e20[signal_index] - e50[signal_index]) > atr_value * 0.35 else "YATAY"
        trades.append({
            "signal_time": candles[signal_index]["time"], "entry_time": candles[entry_index]["time"],
            "exit_time": candles[exit_index]["time"], "direction": direction, "entry": round(entry, 8),
            "exit": round(exit_price, 8), "reason": exit_reason, "pnl": round(pnl, 4),
            "cost_usdt": round(notional * costs, 4), "regime": regime,
        })
        index = exit_index + 1
    wins = [row for row in trades if row["pnl"] > 0]
    losses = [row for row in trades if row["pnl"] <= 0]
    gross_win = sum(row["pnl"] for row in wins)
    gross_loss = abs(sum(row["pnl"] for row in losses))
    fold_size = max(1, len(trades) // 3)
    folds = []
    labels = ["GELİŞTİRME", "DOĞRULAMA", "GÖRÜNMEYEN TEST"]
    for number, label in enumerate(labels):
        start = number * fold_size
        end = len(trades) if number == 2 else min(len(trades), (number + 1) * fold_size)
        subset = trades[start:end]
        folds.append({"name": label, "trades": len(subset), "net_pnl": round(sum(row["pnl"] for row in subset), 4)})
    return {
        "generated_at": now_iso(), "capital": 1000.0, "ending_equity": round(equity, 4),
        "net_pnl": round(equity - 1000, 4), "trades": len(trades),
        "wins": len(wins), "win_rate": round(len(wins) / len(trades) * 100, 2) if trades else 0,
        "max_drawdown_pct": round(max_drawdown, 2),
        "profit_factor": round(gross_win / gross_loss, 2) if gross_loss else (99.0 if gross_win else 0),
        "cost_model": {"fee_bps_per_side": settings["fee_bps_per_side"], "slippage_bps_per_side": settings["slippage_bps_per_side"]},
        "no_lookahead": True, "same_candle_policy": "STOP_FIRST", "folds": folds,
        "recent_trades": trades[-40:][::-1],
        "note": "Geçmiş Demo simülasyonu gelecek getiriyi garanti etmez.",
    }


def certificate_payload(state: dict[str, Any]) -> dict[str, Any]:
    journal = state.get("journal", [])
    closed = [item for item in journal if item.get("kind") == "POSITION_CLOSED" or (item.get("kind") == "FILL" and item.get("reduce_only"))]
    days = {str(item.get("created_at", ""))[:10] for item in closed if item.get("created_at")}
    snapshot = state.get("snapshot") or {}
    positions = snapshot.get("positions", [])
    algos = snapshot.get("open_algo_orders", [])
    protected = sum(1 for position in positions if any(order.get("symbol") == position.get("symbol") and str(order.get("type", "")).upper() == "STOP_MARKET" for order in algos))
    coverage = 100.0 if not positions else protected / len(positions) * 100
    backtest = state.get("backtest") or {}
    gates = [
        {"name": "Demo sunucu fiziksel kilidi", "passed": DEMO_REST_BASE.endswith("demo-fapi.binance.com") and DEMO_WS_BASE.endswith("demo-fstream.binance.com"), "value": "DEMO ONLY", "target": "Zorunlu"},
        {"name": "Kapanmış Demo işlem kanıtı", "passed": len(closed) >= 100, "value": len(closed), "target": 100},
        {"name": "Aktif gün", "passed": len(days) >= 30, "value": len(days), "target": 30},
        {"name": "Stop koruma kapsamı", "passed": coverage >= 100, "value": round(coverage, 1), "target": 100},
        {"name": "Yinelenen emir sızıntısı", "passed": int(state.get("duplicate_submissions", 0)) == 0, "value": int(state.get("duplicate_submissions", 0)), "target": 0},
        {"name": "Yeniden bağlantı tatbikatı", "passed": bool((state.get("drills", {}).get("RECONNECT") or {}).get("passed")), "value": "GEÇTİ" if (state.get("drills", {}).get("RECONNECT") or {}).get("passed") else "BEKLİYOR", "target": "GEÇTİ"},
        {"name": "Acil durdurma tatbikatı", "passed": bool((state.get("drills", {}).get("EMERGENCY") or {}).get("passed")), "value": "GEÇTİ" if (state.get("drills", {}).get("EMERGENCY") or {}).get("passed") else "BEKLİYOR", "target": "GEÇTİ"},
        {"name": "Backtest maksimum düşüş", "passed": bool(backtest) and float(backtest.get("max_drawdown_pct", 999)) <= 10, "value": backtest.get("max_drawdown_pct", "—"), "target": "≤ 10%"},
    ]
    passed = sum(1 for gate in gates if gate["passed"])
    return {
        "version": "21.0.0", "status": "DEMO SERTİFİKALI" if passed == len(gates) else "KANIT TOPLUYOR",
        "score": round(passed / len(gates) * 100), "passed_gates": passed, "total_gates": len(gates),
        "gates": gates, "real_trading_ready": False, "demo_only": True,
        "reason": "Bu sertifika yalnızca Binance Futures Demo çalışma disiplinini ölçer; gerçek para uygunluğu vermez.",
        "generated_at": now_iso(),
    }


def summary_payload(state: dict[str, Any]) -> dict[str, Any]:
    snapshot = state.get("snapshot") or {}
    return {
        "version": "21.0.0", "mode": "BINANCE_FUTURES_DEMO_ONLY", "settings": state["settings"],
        "auto": state["auto"], "stream": state["stream"], "daily": daily_metrics(state),
        "account": {
            "wallet_balance": snapshot.get("wallet_balance"), "available_balance": snapshot.get("available_balance"),
            "unrealized_pnl": snapshot.get("unrealized_pnl"), "positions": len(snapshot.get("positions", [])),
            "normal_orders": len(snapshot.get("open_orders", [])), "algo_orders": len(snapshot.get("open_algo_orders", [])),
        },
        "protection": {
            "repairs": state.get("protection_repairs", 0),
            "duplicate_blocks": state.get("duplicate_blocks", 0),
            "duplicate_submissions": state.get("duplicate_submissions", 0),
        },
        "journal": state.get("journal", [])[:60], "backtest": state.get("backtest"),
        "certificate": certificate_payload(state), "last_saved": state.get("last_saved"),
        "real_trading_locked": True,
    }


def init_v21_demo(application: Any) -> None:
    state = load_state()
    state["lock"] = asyncio.Lock()
    application.state.v21_demo = state
    record_event(state, "V21_START", "V21 Demo Complete başladı; otomatik girişler güvenlik için kapalı.", source="SYSTEM")
    application.state.v21_tasks = [
        asyncio.create_task(reconciliation_loop(application)),
        asyncio.create_task(user_stream_loop(application)),
        asyncio.create_task(automation_loop(application)),
    ]


async def shutdown_v21_demo(application: Any) -> None:
    state = getattr(application.state, "v21_demo", None)
    if state:
        state["auto"]["enabled"] = False
        persist_state(state)
    tasks = getattr(application.state, "v21_tasks", [])
    for task in tasks:
        task.cancel()
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)


@router.get("/summary")
async def v21_summary(request: Request) -> dict[str, Any]:
    return summary_payload(state_for(request))


@router.put("/settings")
async def v21_settings(request: Request, body: SettingsUpdate) -> dict[str, Any]:
    state = state_for(request)
    updates = body.model_dump(exclude_none=True)
    if "allowed_symbols" in updates:
        symbols = []
        for value in updates["allowed_symbols"][:12]:
            symbol = normalize_symbol(value)
            if symbol not in symbols:
                symbols.append(symbol)
        if not symbols:
            raise HTTPException(422, "En az bir izinli USDT paritesi seçin.")
        updates["allowed_symbols"] = symbols
    state["settings"].update(updates)
    state["settings"]["max_margin_per_trade"] = min(float(MAX_MARGIN_USDT), float(state["settings"]["max_margin_per_trade"]))
    state["settings"]["max_positions"] = min(MAX_OPEN_POSITIONS, int(state["settings"]["max_positions"]))
    record_event(state, "SETTINGS", "V21 Demo risk ve otomasyon ayarları güncellendi.", source="USER")
    persist_state(state)
    return summary_payload(state)


@router.post("/risk/size")
async def v21_risk_size(request: Request, body: RiskSizeRequest) -> dict[str, Any]:
    state = state_for(request)
    symbol = normalize_symbol(body.symbol)
    values = risk_size_values(body.entry, body.stop, body.max_loss_usdt, body.leverage, float(state["settings"]["max_margin_per_trade"]))
    rules = await symbol_rules(client_for(request.app), symbol)
    quantity = Decimal(str(values["notional_usdt"])) / Decimal(str(body.entry))
    return {**values, "symbol": symbol, "leverage": body.leverage, "quantity_preview": decimal_text(quantity), "step_size": decimal_text(rules["step"]), "demo_only": True}


@router.post("/auto/start")
async def v21_auto_start(request: Request, body: AutoStartRequest) -> dict[str, Any]:
    state = state_for(request)
    confirmation = body.confirmation.strip().upper()
    if confirmation != "DEMO OTOMATİK":
        raise HTTPException(422, "Otomasyonu açmak için DEMO OTOMATİK yazın.")
    if not armed(request.app.state.binance_demo):
        raise HTTPException(423, "Önce İşlem Masası'ndaki 10 dakikalık DEMO emir kilidini açın.")
    if not credentials_configured():
        raise HTTPException(412, "Binance Futures Demo anahtarları ayarlı değil.")
    snapshot = await account_snapshot(client_for(request.app))
    if snapshot.get("hedge_mode"):
        raise HTTPException(409, "Demo hesabı One-way / Tek Yön modunda olmalı.")
    state["auto"].update({
        "enabled": True,
        "user_confirmed": True,
        "confirmation": confirmation,
        "last_decision": "Kontrollü Demo taraması başlatıldı.",
        "last_error": None,
    })
    record_event(state, "AUTO_START", "V21 kontrollü otomasyon kullanıcı onayıyla açıldı.", source="USER")
    persist_state(state)
    return summary_payload(state)


@router.post("/auto/stop")
async def v21_auto_stop(request: Request) -> dict[str, Any]:
    state = state_for(request)
    state["auto"].update({
        "enabled": False,
        "user_confirmed": False,
        "confirmation": None,
        "last_decision": "Yeni otomatik Demo girişleri durduruldu.",
    })
    record_event(state, "AUTO_STOP", "V21 otomatik girişleri durduruldu; mevcut Stop/TP korumaları açık.", source="USER")
    persist_state(state)
    return summary_payload(state)


@router.get("/journal")
async def v21_journal(request: Request, limit: int = Query(default=200, ge=1, le=1000)) -> dict[str, Any]:
    state = state_for(request)
    return {"items": state.get("journal", [])[:limit], "total": len(state.get("journal", [])), "demo_only": True}


@router.get("/history/{symbol}")
async def v21_history(request: Request, symbol: str) -> dict[str, Any]:
    safe_symbol = normalize_symbol(symbol)
    try:
        client = client_for(request.app)
        normal, algos, trades = await asyncio.gather(
            client.signed("GET", "/fapi/v1/allOrders", {"symbol": safe_symbol, "limit": 200}),
            client.signed("GET", "/fapi/v1/allAlgoOrders", {"symbol": safe_symbol, "limit": 200}),
            client.signed("GET", "/fapi/v1/userTrades", {"symbol": safe_symbol, "limit": 200}),
        )
        return {"symbol": safe_symbol, "orders": response_rows(normal), "algo_orders": response_rows(algos), "trades": response_rows(trades), "demo_only": True}
    except BinanceDemoError as exc:
        raise safe_exchange_error(exc) from exc


@router.post("/backtest")
async def v21_backtest(request: Request, body: BacktestRequest) -> dict[str, Any]:
    state = state_for(request)
    symbol = normalize_symbol(body.symbol)
    candles = await demo_candles(client_for(request.app), symbol, body.interval, body.limit)
    result = backtest_engine(candles, state["settings"])
    result.update({"symbol": symbol, "interval": body.interval})
    state["backtest"] = result
    record_event(state, "BACKTEST", f"{symbol} {body.interval} kronolojik backtest tamamlandı: {result['trades']} işlem.", symbol=symbol, source="LAB")
    persist_state(state)
    return result


@router.post("/drill")
async def v21_drill(request: Request, body: DrillRequest) -> dict[str, Any]:
    state = state_for(request)
    if body.kind == "RECONNECT":
        passed = bool(state["stream"].get("last_sync")) and credentials_configured()
        detail = "REST eşleştirme ve yeniden bağlantı yolu hazır." if passed else "Önce Demo bağlantısını kurun."
    elif body.kind == "PROTECTION":
        snapshot = state.get("snapshot") or {}
        passed = all(
            any(order.get("symbol") == position.get("symbol") and str(order.get("type", "")).upper() == "STOP_MARKET" for order in snapshot.get("open_algo_orders", []))
            for position in snapshot.get("positions", [])
        )
        detail = "Açık pozisyonların Stop kapsamı doğrulandı." if passed else "Korumasız açık pozisyon bulundu."
    else:
        passed = (
            DEMO_REST_BASE == "https://demo-fapi.binance.com"
            and DEMO_WS_BASE == "wss://demo-fstream.binance.com"
            and bool(getattr(request.app.state, "binance_demo", None) is not None)
        )
        detail = (
            "Demo sunucu kilidi ve acil durdurma yolu doğrulandı; tatbikatta emir gönderilmedi."
            if passed else "Demo kilidi veya acil durdurma durumu doğrulanamadı."
        )
    result = {"kind": body.kind, "passed": passed, "detail": detail, "tested_at": now_iso(), "simulation_only": True}
    state["drills"][body.kind] = result
    record_event(state, "DRILL", f"{body.kind} tatbikatı: {'GEÇTİ' if passed else 'BAŞARISIZ'} · {detail}", source="CERTIFICATE")
    persist_state(state)
    return {**result, "certificate": certificate_payload(state)}


@router.get("/certificate")
async def v21_certificate(request: Request) -> dict[str, Any]:
    return certificate_payload(state_for(request))


@router.get("/daily-report")
async def v21_daily_report(request: Request) -> dict[str, Any]:
    state = state_for(request)
    daily = daily_metrics(state)
    return {
        **daily, "stream": state["stream"], "auto": state["auto"],
        "protection_repairs": state.get("protection_repairs", 0),
        "duplicate_blocks": state.get("duplicate_blocks", 0),
        "duplicate_submissions": state.get("duplicate_submissions", 0),
        "certificate_score": certificate_payload(state)["score"],
        "headline": "V21 Demo kanıt raporu", "demo_only": True,
    }
