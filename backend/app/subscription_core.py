"""Central subscription plans and entitlement helpers.

Payment collection is intentionally provider-neutral. Stripe can be attached to
this contract later without allowing the browser to grant access by itself.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

TRIAL_DAYS = 7
PLAN_CATALOG: dict[str, dict[str, Any]] = {
    "STARTER": {"monthly_price": 19, "annual_price": 190, "features": ["Demo trading access", "Basic market analysis", "Standard dashboard access", "Basic trading intelligence", "Limited bot usage", "Limited active positions", "Standard strategies"], "entitlements": {"canUseDemoTrading": True, "canUseLiveTrading": False, "canUseAdvancedAnalytics": False, "canUseBacktesting": False, "canUseAdvancedAI": False, "maxActivePositions": 1}},
    "PRO": {"monthly_price": 39, "annual_price": 390, "features": ["Everything in Starter", "Live trading access", "Advanced risk management", "Advanced market intelligence", "More active positions", "Trading automation", "Advanced performance analytics", "Advanced dashboard features"], "entitlements": {"canUseDemoTrading": True, "canUseLiveTrading": True, "canUseAdvancedAnalytics": True, "canUseBacktesting": True, "canUseAdvancedAI": False, "maxActivePositions": 3}},
    "ELITE": {"monthly_price": 79, "annual_price": 790, "features": ["Everything in Pro", "Highest position limits", "Advanced AI trading intelligence", "Advanced backtesting", "Advanced market analytics", "Priority support", "Early access to new features", "Advanced risk controls"], "entitlements": {"canUseDemoTrading": True, "canUseLiveTrading": True, "canUseAdvancedAnalytics": True, "canUseBacktesting": True, "canUseAdvancedAI": True, "maxActivePositions": 5}},
}


def active_subscription(state: dict[str, Any], user_id: str) -> dict[str, Any] | None:
    now = datetime.now(timezone.utc)
    rows = [row for row in state.get("subscriptions", []) if row.get("user_id") == user_id and row.get("status") in {"ACTIVE", "TRIAL", "CANCELED", "PAST_DUE"}]
    valid = []
    for row in rows:
        end = row.get("currentPeriodEnd") or row.get("trialEnd") or row.get("period_end")
        try:
            expiry = datetime.fromisoformat(str(end).replace("Z", "+00:00")) if end else datetime.fromtimestamp(0, timezone.utc)
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if expiry > now:
            valid.append(row)
    return max(valid, key=lambda row: row.get("currentPeriodEnd") or row.get("trialEnd") or row.get("period_end") or "", default=None)


def entitlement_snapshot(state: dict[str, Any], user_id: str) -> dict[str, Any]:
    row = active_subscription(state, user_id)
    if not row:
        return {"status": "FREE", "plan": None, "features": [], "entitlements": {"canUseDemoTrading": False, "canUseLiveTrading": False, "canUseAdvancedAnalytics": False, "canUseBacktesting": False, "canUseAdvancedAI": False, "maxActivePositions": 0}, "mode": "DEVELOPMENT", "cancelAtPeriodEnd": False}
    plan = str(row.get("plan") or "STARTER").upper()
    catalog = PLAN_CATALOG.get(plan, PLAN_CATALOG["STARTER"])
    status = row.get("status", "ACTIVE")
    entitlements = catalog["entitlements"] if status != "PAST_DUE" else {key: False if isinstance(value, bool) else 0 for key, value in catalog["entitlements"].items()}
    return {"status": status, "plan": plan, "billingInterval": row.get("billingInterval") or row.get("billing_interval", "monthly"), "trialStart": row.get("trialStart"), "trialEnd": row.get("trialEnd"), "currentPeriodStart": row.get("currentPeriodStart"), "currentPeriodEnd": row.get("currentPeriodEnd") or row.get("period_end"), "currentPrice": row.get("currentPrice"), "features": catalog["features"] if status != "PAST_DUE" else [], "entitlements": entitlements, "mode": "STRIPE" if row.get("provider") == "STRIPE" else "DEVELOPMENT", "cancelAtPeriodEnd": bool(row.get("cancelAtPeriodEnd", False))}
