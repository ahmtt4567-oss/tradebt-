"""V24 commercial launch helpers.

This module is deliberately dependency free.  It calculates Demo invoices and
launch/onboarding readiness, but never handles card data or enables payments.
"""

from __future__ import annotations

from typing import Any


SUPPORTED_CURRENCIES = {"USD", "EUR", "TRY", "USDT"}


def default_business_settings() -> dict[str, Any]:
    return {
        "brand_name": "ProTreBot Elite X",
        "legal_name": "",
        "support_email": "",
        "website_url": "",
        "currency": "USD",
        "trial_days": 14,
        "terms_version": "V24-DEMO-1",
        "country": "Türkiye",
        "payment_provider": "NOT_CONFIGURED",
        "checkout_live": False,
        "card_data_collected": False,
    }


def sanitize_business_settings(payload: Any) -> dict[str, Any]:
    base = default_business_settings()
    if not isinstance(payload, dict):
        return base
    text_limits = {
        "brand_name": 80,
        "legal_name": 120,
        "support_email": 180,
        "website_url": 240,
        "terms_version": 40,
        "country": 80,
    }
    for key, limit in text_limits.items():
        value = payload.get(key)
        if isinstance(value, str):
            base[key] = value.strip()[:limit]
    currency = str(payload.get("currency", "USD")).upper()
    base["currency"] = currency if currency in SUPPORTED_CURRENCIES else "USD"
    try:
        base["trial_days"] = min(90, max(1, int(payload.get("trial_days", 14))))
    except (TypeError, ValueError):
        base["trial_days"] = 14
    # V24 is a launch lab.  These values cannot be restored as enabled from disk.
    base["payment_provider"] = "NOT_CONFIGURED"
    base["checkout_live"] = False
    base["card_data_collected"] = False
    return base


def calculate_demo_invoice(
    *,
    plan_code: str,
    plan: dict[str, Any],
    months: int = 1,
    discount_pct: float = 0.0,
    tax_pct: float = 0.0,
    currency: str = "USD",
) -> dict[str, Any]:
    months = min(24, max(1, int(months)))
    discount_pct = min(100.0, max(0.0, float(discount_pct)))
    tax_pct = min(100.0, max(0.0, float(tax_pct)))
    unit = max(0.0, float(plan.get("monthly_usd", 0.0)))
    subtotal = unit * months
    discount = subtotal * discount_pct / 100
    taxable = subtotal - discount
    tax = taxable * tax_pct / 100
    total = taxable + tax
    return {
        "plan": plan_code.upper(),
        "plan_name": str(plan.get("name", plan_code)),
        "months": months,
        "unit_price": round(unit, 2),
        "subtotal": round(subtotal, 2),
        "discount_pct": round(discount_pct, 2),
        "discount": round(discount, 2),
        "tax_pct": round(tax_pct, 2),
        "tax": round(tax, 2),
        "total": round(total, 2),
        "currency": currency if currency in SUPPORTED_CURRENCIES else "USD",
        "payment_status": "DEMO_PREVIEW",
        "collects_money": False,
        "demo_only": True,
    }


def launch_checklist(settings: dict[str, Any], evidence: dict[str, Any]) -> list[dict[str, Any]]:
    support_email = str(settings.get("support_email", ""))
    website_url = str(settings.get("website_url", ""))
    legal_name = str(settings.get("legal_name", ""))
    rows = [
        {"key": "brand", "label": "Marka adı", "passed": bool(settings.get("brand_name")), "detail": "Müşteri ekranlarında görünen ürün adı."},
        {"key": "company", "label": "Şirket / unvan", "passed": bool(legal_name), "detail": "Fatura ve sözleşme tarafı daha sonra doğrulanacak."},
        {"key": "support", "label": "Destek kanalı", "passed": "@" in support_email, "detail": "Müşteri destek e-postası."},
        {"key": "website", "label": "Alan adı / site", "passed": website_url.startswith(("https://", "http://")), "detail": "Tanıtım ve müşteri giriş adresi."},
        {"key": "terms", "label": "Koşullar ve risk metni", "passed": evidence.get("legal", {}).get("status") == "RECORDED", "detail": "Ülkeye özel hukuk incelemesi gerektirir."},
        {"key": "security", "label": "Bağımsız güvenlik testi", "passed": evidence.get("security_review", {}).get("status") == "RECORDED", "detail": "Genel satış öncesi pentest gerektirir."},
        {"key": "backup", "label": "Yedekleme tatbikatı", "passed": evidence.get("backup", {}).get("status") == "RECORDED", "detail": "Geri yüklenebilir yedek kanıtı."},
        {"key": "billing", "label": "Canlı ödeme sağlayıcısı", "passed": False, "detail": "V24 paketinde bilinçli olarak kapalı; sağlayıcı hesabı daha sonra bağlanacak."},
    ]
    return rows
