"""V25.1 Paper-only autonomous ranking and capital allocation helpers.

The functions in this module are deliberately pure.  They never call an
exchange, create an order, or change application state.  The FastAPI Paper
engine remains the only caller that may open a simulated position.
"""

from __future__ import annotations

import math
from typing import Iterable


PAPER_AUTONOMY_VERSION = "25.1.0"
PAPER_DAILY_REFERENCE_USDT = 5.0
PAPER_FEE_RATE = 0.001


def autonomy_policy(profile: str | None) -> dict:
    """Return bounded Paper-only scan and allocation limits for a profile."""
    normalized = str(profile or "DENGELI").strip().upper().replace("İ", "I")
    policies = {
        "TEMKINLI": {
            "universe_size": 18,
            "shortlist_size": 6,
            "risk_per_trade_pct": 0.18,
            "max_allocation_pct": 8.0,
            "max_total_exposure_pct": 24.0,
            "minimum_projected_net_usdt": 2.5,
        },
        "DENGELI": {
            "universe_size": 24,
            "shortlist_size": 8,
            "risk_per_trade_pct": 0.30,
            "max_allocation_pct": 15.0,
            "max_total_exposure_pct": 45.0,
            "minimum_projected_net_usdt": 5.0,
        },
        "HIZLI": {
            "universe_size": 30,
            "shortlist_size": 10,
            "risk_per_trade_pct": 0.40,
            "max_allocation_pct": 18.0,
            "max_total_exposure_pct": 54.0,
            "minimum_projected_net_usdt": 5.0,
        },
    }
    key = normalized if normalized in policies else "DENGELI"
    return {
        "version": PAPER_AUTONOMY_VERSION,
        "profile": key,
        **policies[key],
        "maximum_positions": 3,
        "maximum_order_usdt": 2_000.0,
        "daily_reference_usdt": PAPER_DAILY_REFERENCE_USDT,
        "profit_guaranteed": False,
        "orders_enabled": False,
        "testnet_orders_enabled": False,
        "paper_only": True,
    }


def _number(value: object, default: float = 0.0) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return parsed if math.isfinite(parsed) else default


def rank_paper_candidates(rows: Iterable[dict], profile: str | None = None) -> list[dict]:
    """Rank LONG/SHORT scan rows and retain transparent eligibility reasons."""
    policy = autonomy_policy(profile)
    ranked: list[dict] = []
    for row in rows:
        direction = str(row.get("direction") or "BEKLE").upper()
        if direction not in {"LONG", "SHORT"}:
            continue
        confidence = max(0.0, min(100.0, _number(row.get("confidence"))))
        trap_score = max(0.0, min(100.0, _number(row.get("trap_score"), 100.0)))
        volume_ratio = max(0.0, _number(row.get("volume_ratio")))
        change = _number(row.get("change"))
        breakout = bool(row.get("breakout"))
        confidence_ok = confidence >= _number(row.get("minimum_confidence"), 0.0)
        # The profile threshold is authoritative; a row-level threshold may only
        # make the row stricter, never looser.
        confidence_floor = max(
            _number(row.get("minimum_confidence"), 0.0),
            _number(row.get("profile_minimum_confidence"), 0.0),
        )
        if confidence_floor <= 0:
            confidence_floor = {"TEMKINLI": 84.0, "DENGELI": 75.0, "HIZLI": 70.0}[policy["profile"]]
        confidence_ok = confidence >= confidence_floor
        trap_ok = trap_score <= {"TEMKINLI": 35.0, "DENGELI": 50.0, "HIZLI": 60.0}[policy["profile"]]
        eligible = confidence_ok and trap_ok
        if not confidence_ok:
            status = f"GÜVEN BEKLİYOR · %{confidence:.0f}/{confidence_floor:.0f}"
        elif not trap_ok:
            status = f"TUZAK RİSKİ · %{trap_score:.0f}"
        else:
            status = "ÖN ADAY"

        score = (
            confidence * 0.66
            + min(volume_ratio, 3.0) * 6.0
            + min(abs(change), 12.0) * 0.45
            + (6.0 if breakout else 0.0)
            - trap_score * 0.18
        )
        ranked.append({
            "symbol": str(row.get("symbol") or ""),
            "display": str(row.get("display") or row.get("symbol") or ""),
            "direction": direction,
            "confidence": round(confidence),
            "trap_score": round(trap_score),
            "volume_ratio": round(volume_ratio, 2),
            "change": round(change, 2),
            "price": _number(row.get("price")),
            "volume": _number(row.get("volume")),
            "breakout": breakout,
            "edge_score": round(max(0.0, min(99.0, score)), 1),
            "eligible": eligible,
            "status": status,
        })
    ranked.sort(
        key=lambda item: (
            bool(item["eligible"]),
            _number(item["edge_score"]),
            _number(item["confidence"]),
            _number(item["volume"]),
        ),
        reverse=True,
    )
    shortlist = ranked[: int(policy["shortlist_size"])]
    for index, item in enumerate(shortlist, start=1):
        item["rank"] = index
    return shortlist


def dynamic_paper_allocation(
    *,
    balance: float,
    available: float,
    current_exposure: float,
    entry_price: float,
    stop_loss: float,
    tp3: float,
    confidence: float,
    risk_score: float,
    regime_multiplier: float = 1.0,
    profile: str | None = None,
) -> dict:
    """Size a Paper position from stop risk, cash, exposure, and signal quality.

    The projected net result follows the actual 35/35/30 percent TP1/TP2/TP3
    lifecycle used by the Paper engine and subtracts its closing fee model.
    It is a scenario, never a prediction or a profit promise.
    """
    policy = autonomy_policy(profile)
    balance = max(0.0, _number(balance))
    available = max(0.0, _number(available))
    current_exposure = max(0.0, _number(current_exposure))
    entry = max(0.0, _number(entry_price))
    stop = max(0.0, _number(stop_loss))
    target = max(0.0, _number(tp3))
    confidence = max(0.0, min(100.0, _number(confidence)))
    risk_score = max(0.0, min(100.0, _number(risk_score)))
    regime = max(0.35, min(1.25, _number(regime_multiplier, 1.0)))

    if entry <= 0 or stop <= 0 or target <= 0 or balance <= 0:
        return {
            "approved": False,
            "status": "GEÇERSİZ PLAN",
            "reason": "Giriş, Stop, TP3 ve sanal bakiye pozitif olmalı.",
            "amount": 0.0,
        }

    stop_pct = abs(entry - stop) / entry
    target_pct = abs(target - entry) / entry
    if stop_pct < 0.0005 or target_pct <= stop_pct:
        return {
            "approved": False,
            "status": "RİSK/HEDEF UYGUN DEĞİL",
            "reason": "Stop mesafesi veya TP3 risk/ödül yapısı uygun değil.",
            "amount": 0.0,
            "stop_distance_pct": round(stop_pct * 100, 3),
            "tp3_distance_pct": round(target_pct * 100, 3),
        }

    quality_factor = 0.70 + (confidence / 100.0) * 0.30
    risk_factor = max(0.40, 1.0 - risk_score / 125.0)
    risk_budget = balance * (_number(policy["risk_per_trade_pct"]) / 100.0)
    risk_budget *= quality_factor * risk_factor * regime
    stop_sized_notional = risk_budget / stop_pct
    allocation_cap = balance * (_number(policy["max_allocation_pct"]) / 100.0)
    exposure_cap = balance * (_number(policy["max_total_exposure_pct"]) / 100.0)
    exposure_room = max(0.0, exposure_cap - current_exposure)
    raw_amount = min(
        stop_sized_notional,
        allocation_cap,
        exposure_room,
        available,
        _number(policy["maximum_order_usdt"]),
    )
    amount = math.floor(max(0.0, raw_amount) / 10.0) * 10.0

    # TP plan: 35% at 1R, 35% at 2R, and 30% at 3R.
    planned_gross_rate = stop_pct * (0.35 + 0.70 + 0.90)
    projected_plan_net = amount * planned_gross_rate - amount * PAPER_FEE_RATE
    projected_stop_loss = amount * stop_pct + amount * PAPER_FEE_RATE
    projected_tp3_full_net = amount * target_pct - amount * PAPER_FEE_RATE
    minimum_net = _number(policy["minimum_projected_net_usdt"])

    approved = amount >= 50.0 and projected_plan_net >= minimum_net
    if amount < 50.0:
        status = "SERMAYE BEKLİYOR"
        reason = "Kullanılabilir sanal bakiye veya toplam maruziyet payı 50 USDT altında."
    elif projected_plan_net < minimum_net:
        status = "NET FIRSAT YETERSİZ"
        reason = (
            f"Kısmi TP planı net senaryosu {projected_plan_net:.2f} USDT; "
            f"{minimum_net:.2f} USDT profil eşiğinin altında."
        )
    else:
        status = "TAHSİS HAZIR"
        reason = "Stop riski, portföy maruziyeti ve kısmi kâr planı profil sınırları içinde."

    return {
        "approved": approved,
        "status": status,
        "reason": reason,
        "amount": round(amount, 2),
        "risk_budget_usdt": round(risk_budget, 2),
        "projected_stop_loss_usdt": round(projected_stop_loss, 2),
        "projected_plan_net_usdt": round(projected_plan_net, 2),
        "projected_tp3_full_net_usdt": round(projected_tp3_full_net, 2),
        "minimum_projected_net_usdt": minimum_net,
        "stop_distance_pct": round(stop_pct * 100, 3),
        "tp3_distance_pct": round(target_pct * 100, 3),
        "allocation_pct": round((amount / balance * 100.0) if balance else 0.0, 2),
        "current_exposure_pct": round((current_exposure / balance * 100.0) if balance else 0.0, 2),
        "maximum_total_exposure_pct": policy["max_total_exposure_pct"],
        "profile": policy["profile"],
        "paper_only": True,
        "profit_guaranteed": False,
        "orders_enabled": False,
        "testnet_orders_enabled": False,
    }


def daily_reference_progress(realized_pnl: float, reference: float = PAPER_DAILY_REFERENCE_USDT) -> dict:
    """Expose an observation target without implying a guaranteed daily return."""
    value = _number(realized_pnl)
    target = max(0.01, _number(reference, PAPER_DAILY_REFERENCE_USDT))
    return {
        "realized_pnl_usdt": round(value, 2),
        "reference_usdt": round(target, 2),
        "progress_pct": round(max(0.0, min(100.0, value / target * 100.0)), 1),
        "status": "REFERANS AŞILDI" if value >= target else "KANIT TOPLANIYOR",
        "profit_guaranteed": False,
        "note": "5 USDT yalnızca gözlem referansıdır; günlük kâr garantisi veya zorunlu işlem hedefi değildir.",
    }
