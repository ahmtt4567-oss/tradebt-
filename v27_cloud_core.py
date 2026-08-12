"""Dependency-free helpers for the V27 durable Testnet ledger."""

from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from typing import Any


VERSION = "27.0.0"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def json_safe(value: Any) -> Any:
    """Return a JSON-safe copy without locks, tasks or credential fields."""
    if value is None or isinstance(value, (bool, str, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {
            str(key): json_safe(item)
            for key, item in value.items()
            if key not in {"lock", "api_key", "secret_key", "credentials"}
        }
    if isinstance(value, (list, tuple, set)):
        return [json_safe(item) for item in value]
    return None


def durable_payload(application: Any) -> dict[str, Any]:
    """Build the allow-listed, non-secret state saved to PostgreSQL."""
    v21 = application.state.v21_demo
    demo = application.state.binance_demo
    return {
        "schema": 1,
        "version": VERSION,
        "saved_at": now_iso(),
        "v21": json_safe({
            "settings": v21.get("settings", {}),
            "journal": v21.get("journal", [])[:1200],
            "seen_event_ids": v21.get("seen_event_ids", [])[-800:],
            "backtest": v21.get("backtest"),
            "drills": v21.get("drills", {}),
            "duplicate_blocks": v21.get("duplicate_blocks", 0),
            "duplicate_submissions": v21.get("duplicate_submissions", 0),
            "protection_repairs": v21.get("protection_repairs", 0),
        }),
        "demo": json_safe({
            "plans": demo.get("plans", {}),
            "events": demo.get("events", [])[:80],
        }),
        "safety": {
            "testnet_only": True,
            "real_orders_enabled": False,
            "automation_resumes_after_restart": False,
        },
    }


def restore_payload(application: Any, payload: Any) -> bool:
    """Restore evidence while keeping all order/automation locks closed."""
    if not isinstance(payload, dict) or int(payload.get("schema", 0)) != 1:
        return False
    stored_v21 = payload.get("v21")
    stored_demo = payload.get("demo")
    if not isinstance(stored_v21, dict) or not isinstance(stored_demo, dict):
        return False

    v21 = application.state.v21_demo
    settings = stored_v21.get("settings")
    if isinstance(settings, dict):
        v21["settings"].update({key: value for key, value in settings.items() if key in v21["settings"]})
    for key in ("journal", "seen_event_ids"):
        value = stored_v21.get(key)
        if isinstance(value, list):
            v21[key] = value
    for key in ("backtest", "drills"):
        value = stored_v21.get(key)
        if value is None or isinstance(value, dict):
            v21[key] = value
    for key in ("duplicate_blocks", "duplicate_submissions", "protection_repairs"):
        try:
            v21[key] = max(0, int(stored_v21.get(key, v21.get(key, 0))))
        except (TypeError, ValueError):
            pass
    v21["auto"].update({
        "enabled": False,
        "busy": False,
        "last_decision": "Bulut kaydı geri yüklendi; DEMO OTOMATİK yeniden kullanıcı onayı bekliyor.",
    })

    plans = stored_demo.get("plans")
    if isinstance(plans, dict):
        application.state.binance_demo["plans"] = plans
    events = stored_demo.get("events")
    if isinstance(events, list):
        application.state.binance_demo["events"] = events[:80]
    application.state.binance_demo.update({"armed_until": 0, "connected": False})
    return True


def evidence_rows(payload: dict[str, Any]) -> list[tuple[str, str, str | None, str, str]]:
    rows: list[tuple[str, str, str | None, str, str]] = []
    for event in payload.get("v21", {}).get("journal", []):
        if not isinstance(event, dict):
            continue
        identity = str(event.get("id") or "")
        if not identity:
            raw = "|".join(str(event.get(key) or "") for key in ("created_at", "kind", "symbol", "message"))
            identity = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        rows.append((
            identity[:128],
            str(event.get("kind") or "EVENT")[:80],
            str(event.get("symbol") or "")[:20] or None,
            str(event.get("created_at") or now_iso()),
            json.dumps(json_safe(event), ensure_ascii=False),
        ))
    return rows

