"""V24 Commercial Complete control plane (keeps the /api/v22 compatibility path).

The endpoints here are a production-shaped local lab: membership, licensing,
device pairing, audit and fee-aware planning.  Billing and exchange execution
remain disabled so this package cannot move real money or place real orders.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import secrets
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from .binance_demo import credentials_configured, public_status as demo_public_status
from .commercial_core import (
    FeeGuardInput,
    V22_VERSION,
    calculate_fee_guard,
    calculate_grid_guard,
    default_commercial_state,
    device_fingerprint_hash,
    hash_password,
    issue_token,
    normalize_email,
    pairing_code_hash,
    verify_password,
    verify_token,
)
from .commerce_core import sanitize_business_settings
from .local_storage import DATA_DIR, migrate_legacy_files
from .web_security import MIN_ACCESS_TOKEN_LENGTH, bootstrap_access_allowed


router = APIRouter(prefix="/api/v22", tags=["V24 Commercial Complete"])
migrate_legacy_files((
    "v22_commercial_state.json",
    "v22_commercial_state.backup.json",
    "v22_server_secret.dat",
))
STATE_PATH = DATA_DIR / "v22_commercial_state.json"
BACKUP_PATH = DATA_DIR / "v22_commercial_state.backup.json"
SECRET_PATH = DATA_DIR / "v22_server_secret.dat"
LOGIN_ATTEMPTS: dict[str, list[float]] = {}
STANDARD_SESSION_SECONDS = 8 * 60 * 60
REMEMBER_SESSION_SECONDS = 30 * 24 * 60 * 60
COMMERCIAL_STATE_KEY = "v22-commercial"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_date(value: str | None) -> datetime:
    try:
        return datetime.fromisoformat(value or "").astimezone(timezone.utc)
    except ValueError:
        return datetime.fromtimestamp(0, timezone.utc)


def load_secret() -> bytes:
    configured = str(os.getenv("PROTREBOT_SESSION_SECRET") or "").strip()
    if len(configured) >= 32:
        return hashlib.sha256(configured.encode("utf-8")).digest()
    web_owner_token = str(os.getenv("PROTREBOT_WEB_ACCESS_TOKEN") or "").strip()
    if len(web_owner_token) >= MIN_ACCESS_TOKEN_LENGTH:
        return hashlib.sha256(f"protrebot-v22-session-v1:{web_owner_token}".encode("utf-8")).digest()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if SECRET_PATH.exists():
        raw = SECRET_PATH.read_bytes()
        if len(raw) >= 32:
            return raw
    raw = secrets.token_bytes(48)
    temp = SECRET_PATH.with_suffix(".tmp")
    temp.write_bytes(raw)
    os.chmod(temp, 0o600)
    temp.replace(SECRET_PATH)
    return raw


def sanitize_state(payload: Any) -> dict[str, Any]:
    base = default_commercial_state()
    if not isinstance(payload, dict):
        return base
    for key in (
        "owner_user_id", "users", "subscriptions", "licenses", "pairing_codes", "agents", "audit",
        "plans", "release_evidence", "leads", "demo_invoices", "support_tickets", "acceptances",
    ):
        if key in payload and isinstance(payload[key], type(base[key])):
            base[key] = payload[key]
    base["business"] = sanitize_business_settings(payload.get("business"))
    # These safety switches are never restored from disk as enabled values.
    base["security"] = default_commercial_state()["security"]
    base["billing"] = {"provider": "MANUAL_DEMO", "live": False, "currency": "USD"}
    base["version"] = V22_VERSION
    return base


def load_state() -> dict[str, Any]:
    for path in (STATE_PATH, BACKUP_PATH):
        try:
            return sanitize_state(json.loads(path.read_text(encoding="utf-8")))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            continue
    return default_commercial_state()


def save_state(state: dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    serializable = sanitize_state(state)
    body = json.dumps(serializable, ensure_ascii=False, indent=2)
    temp = STATE_PATH.with_suffix(".tmp")
    temp.write_text(body, encoding="utf-8")
    if STATE_PATH.exists():
        try:
            BACKUP_PATH.write_text(STATE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
        except OSError:
            pass
    temp.replace(STATE_PATH)
    state["_database_revision"] = int(state.get("_database_revision", 0)) + 1
    state["_database_dirty"] = True


async def ensure_commercial_schema(application: Any) -> None:
    pool = getattr(application.state, "db_pool", None)
    if pool is None:
        return
    await pool.execute(
        """
        CREATE TABLE IF NOT EXISTS application_state_snapshots (
          state_key TEXT PRIMARY KEY,
          updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          payload JSONB NOT NULL
        )
        """
    )


async def persist_v22_commercial(application: Any) -> bool:
    pool = getattr(application.state, "db_pool", None)
    if pool is None or not hasattr(application.state, "v22_commercial"):
        return False
    rt = application.state.v22_commercial
    state = rt["state"]
    revision = int(state.get("_database_revision", 0))
    payload = json.dumps(sanitize_state(state), ensure_ascii=False)
    try:
        async with rt["storage_lock"]:
            await pool.execute(
                """
                INSERT INTO application_state_snapshots (state_key, updated_at, payload)
                VALUES ($1, NOW(), $2::jsonb)
                ON CONFLICT (state_key) DO UPDATE
                SET updated_at = NOW(), payload = EXCLUDED.payload
                """,
                COMMERCIAL_STATE_KEY,
                payload,
            )
        if int(state.get("_database_revision", 0)) == revision:
            state["_database_dirty"] = False
        rt["storage_status"] = "POSTGRESQL_KALICI"
        return True
    except Exception:
        rt["storage_status"] = "YEREL_YEDEK"
        return False


async def restore_v22_commercial(application: Any) -> bool:
    pool = getattr(application.state, "db_pool", None)
    if pool is None or not hasattr(application.state, "v22_commercial"):
        return False
    rt = application.state.v22_commercial
    try:
        row = await pool.fetchrow(
            "SELECT payload FROM application_state_snapshots WHERE state_key = $1",
            COMMERCIAL_STATE_KEY,
        )
    except Exception:
        rt["storage_status"] = "YEREL_YEDEK"
        return False
    if row is None:
        return False
    payload = row["payload"]
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            return False
    if not isinstance(payload, dict):
        return False
    restored = sanitize_state(payload)
    restored["_database_revision"] = 0
    restored["_database_dirty"] = False
    rt["state"] = restored
    rt["storage_status"] = "POSTGRESQL_KALICI"
    return True


async def sync_v22_storage(application: Any) -> None:
    if not hasattr(application.state, "v22_commercial"):
        return
    rt = application.state.v22_commercial
    try:
        if not rt.get("storage_ready"):
            await ensure_commercial_schema(application)
            rt["storage_ready"] = True
        if not rt.get("restore_attempted"):
            restored = await restore_v22_commercial(application)
            rt["restore_attempted"] = True
            if not restored:
                await persist_v22_commercial(application)
        elif rt["state"].get("_database_dirty"):
            await persist_v22_commercial(application)
    except Exception:
        rt["storage_status"] = "YEREL_YEDEK"


def public_user(user: dict[str, Any]) -> dict[str, Any]:
    return {key: user.get(key) for key in ("id", "email", "display_name", "role", "active", "created_at")}


def add_audit(state: dict[str, Any], kind: str, message: str, *, actor: str = "SYSTEM", subject: str | None = None) -> None:
    state["audit"].insert(0, {
        "id": uuid.uuid4().hex,
        "kind": kind,
        "message": message,
        "actor": actor,
        "subject": subject,
        "created_at": now_iso(),
        "demo_only": True,
    })
    del state["audit"][250:]


def runtime(request: Request) -> dict[str, Any]:
    return request.app.state.v22_commercial


def bearer(request: Request) -> str:
    value = request.headers.get("authorization", "")
    if not value.lower().startswith("bearer "):
        raise HTTPException(401, "Oturum gerekli")
    return value.split(" ", 1)[1].strip()


def authenticated_user(request: Request, *, owner: bool = False) -> dict[str, Any]:
    rt = runtime(request)
    try:
        payload = verify_token(bearer(request), rt["secret"], expected_kind="USER")
    except ValueError as exc:
        raise HTTPException(401, str(exc)) from exc
    user = next((item for item in rt["state"]["users"] if item.get("id") == payload["sub"] and item.get("active")), None)
    if not user:
        raise HTTPException(401, "Kullanıcı etkin değil")
    if int(payload.get("ver", 1)) != int(user.get("auth_version", 1)):
        raise HTTPException(401, "Oturum yenilenmeli")
    if owner and user.get("role") != "OWNER":
        raise HTTPException(403, "Yönetici yetkisi gerekli")
    return user


def active_license(state: dict[str, Any], user_id: str) -> dict[str, Any] | None:
    now = datetime.now(timezone.utc)
    candidates = [item for item in state["licenses"] if item.get("user_id") == user_id and item.get("status") == "ACTIVE" and parse_date(item.get("expires_at")) > now]
    return max(candidates, key=lambda item: item.get("expires_at", ""), default=None)


def admin_overview(state: dict[str, Any]) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    active_licenses = [item for item in state["licenses"] if item.get("status") == "ACTIVE" and parse_date(item.get("expires_at")) > now]
    online_cutoff = now - timedelta(minutes=3)
    online_agents = [item for item in state["agents"] if parse_date(item.get("last_seen_at")) >= online_cutoff and item.get("status") == "ACTIVE"]
    return {
        "users": len(state["users"]),
        "active_users": sum(1 for item in state["users"] if item.get("active")),
        "licenses": len(state["licenses"]),
        "active_licenses": len(active_licenses),
        "agents": len(state["agents"]),
        "online_agents": len(online_agents),
        "monthly_demo_revenue_usd": round(sum(float(state["plans"].get(item.get("plan"), {}).get("monthly_usd", 0)) for item in active_licenses), 2),
        "customers": [{**public_user(user), "license": active_license(state, user["id"])} for user in state["users"]],
        "agents_list": state["agents"][-40:],
        "audit": state["audit"][:50],
        "billing_live": False,
        "demo_only": True,
    }


def operations_overview(application: Any) -> dict[str, Any]:
    """Return a secret-free summary of the local professional stack."""
    demo_state = getattr(application.state, "binance_demo", {})
    v21 = getattr(application.state, "v21_demo", {})
    paper = getattr(application.state, "paper", {})
    paper_bot = getattr(application.state, "paper_bot", {})
    infrastructure = getattr(application.state, "infrastructure", {})
    demo = demo_public_status(demo_state) if demo_state else {
        "configured": credentials_configured(), "connected": False, "armed": False,
        "events": [], "real_trading_locked": True,
    }
    snapshot = v21.get("snapshot") or {}
    return {
        "version": V22_VERSION,
        "demo_connector": {
            "configured": bool(demo.get("configured")),
            "connected": bool(demo.get("connected")),
            "armed": bool(demo.get("armed")),
            "armed_until": demo.get("armed_until"),
            "last_error": demo.get("last_error"),
        },
        "demo_account": {
            "positions": len(snapshot.get("positions", [])),
            "open_orders": len(snapshot.get("open_orders", [])),
            "open_algo_orders": len(snapshot.get("open_algo_orders", [])),
            "available_balance": snapshot.get("available_balance"),
            "wallet_balance": snapshot.get("wallet_balance"),
            "one_way": not bool(snapshot.get("hedge_mode", False)),
        },
        "automation": {
            "demo_enabled": bool(v21.get("auto", {}).get("enabled")),
            "demo_cycles": int(v21.get("auto", {}).get("cycles", 0)),
            "demo_last_decision": v21.get("auto", {}).get("last_decision"),
            "paper_enabled": bool(paper_bot.get("enabled")),
            "paper_cycles": int(paper_bot.get("cycles", 0)),
        },
        "paper": {
            "balance": paper.get("balance", 0),
            "positions": len(paper.get("positions", [])),
            "pending_orders": len(paper.get("limit_orders", [])),
            "closed_trades": len(paper.get("trades", [])),
            "emergency_brake": bool(paper.get("emergency_brake", {}).get("active")),
        },
        "services": {
            "api": infrastructure.get("api", "BAĞLI"),
            "database": infrastructure.get("database", "BEKLENİYOR"),
            "redis": infrastructure.get("redis", "BEKLENİYOR"),
            "paper_storage": infrastructure.get("paper_storage", "BEKLENİYOR"),
        },
        "recent_demo_events": demo.get("events", [])[:8],
        "real_orders_enabled": False,
        "testnet_orders_enabled": False,
        "withdrawals_supported": False,
        "demo_only": True,
    }


class BootstrapRequest(BaseModel):
    display_name: str = Field(min_length=2, max_length=80)
    email: str = Field(min_length=5, max_length=180)
    password: str = Field(min_length=10, max_length=256)
    remember: bool = True


class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=180)
    password: str = Field(min_length=1, max_length=256)
    remember: bool = False


class CustomerRequest(BootstrapRequest):
    plan: Literal["TRIAL", "STARTER", "PRO", "ELITE"] = "TRIAL"
    days: int = Field(default=14, ge=1, le=730)


class SubscriptionRequest(BaseModel):
    user_id: str = Field(min_length=8, max_length=80)
    plan: Literal["TRIAL", "STARTER", "PRO", "ELITE"]
    days: int = Field(default=30, ge=1, le=730)


class PlanUpdateRequest(BaseModel):
    monthly_usd: float = Field(ge=0, le=100_000)
    agents: int = Field(ge=1, le=1_000)
    bots: int = Field(ge=1, le=10_000)


class PairAgentRequest(BaseModel):
    code: str = Field(min_length=6, max_length=24)
    device_name: str = Field(min_length=2, max_length=100)
    fingerprint: str = Field(min_length=12, max_length=500)


class HeartbeatRequest(BaseModel):
    app_version: str = Field(default=V22_VERSION, max_length=40)
    status: str = Field(default="READY", max_length=40)


class FeeGuardRequest(BaseModel):
    entry: float = Field(gt=0)
    target: float = Field(gt=0)
    notional_usdt: float = Field(gt=0, le=1_000_000)
    direction: Literal["LONG", "SHORT"] = "LONG"
    fee_bps_per_side: float = Field(default=4.0, ge=0, le=500)
    slippage_bps_per_side: float = Field(default=2.0, ge=0, le=500)
    funding_bps: float = Field(default=0.0, ge=-500, le=500)
    minimum_net_usdt: float = Field(default=0.25, ge=0, le=100_000)
    minimum_net_pct: float = Field(default=0.05, ge=0, le=100)


class GridGuardRequest(BaseModel):
    lower: float = Field(gt=0)
    upper: float = Field(gt=0)
    grid_count: int = Field(default=20, ge=3, le=200)
    capital_usdt: float = Field(default=1_000, gt=0, le=1_000_000)
    maker_share_pct: float = Field(default=80, ge=0, le=100)
    maker_fee_bps: float = Field(default=2.0, ge=0, le=500)
    taker_fee_bps: float = Field(default=5.0, ge=0, le=500)
    slippage_bps_per_side: float = Field(default=1.0, ge=0, le=500)
    funding_bps: float = Field(default=0.0, ge=-500, le=500)
    minimum_cycle_net_usdt: float = Field(default=0.05, ge=0, le=100_000)


class CustomerStatusRequest(BaseModel):
    active: bool
    reason: str = Field(default="Yönetici işlemi", max_length=180)


class RevokeRequest(BaseModel):
    confirmation: str = Field(min_length=3, max_length=40)
    reason: str = Field(default="Yönetici işlemi", max_length=180)


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=10, max_length=256)


class ReleaseEvidenceRequest(BaseModel):
    status: Literal["PENDING", "RECORDED"]
    note: str = Field(min_length=3, max_length=500)


@router.get("/public")
async def v22_public(request: Request):
    rt = runtime(request)
    state = rt["state"]
    return {
        "version": V22_VERSION,
        "edition": "COMMERCIAL COMPLETE · LAUNCH LAB",
        "setup_required": not bool(state.get("owner_user_id")),
        "plans": state["plans"],
        "billing": state["billing"],
        "security": state["security"],
        "account_storage": "WINDOWS_LOCAL_APP_DATA" if os.name == "nt" else rt.get("storage_status", "YEREL_YEDEK"),
        "message": "Üyelik, lisans, yerel ajan, satış ve müşteri kurulum altyapısı tek Demo/Paper paketinde; gerçek para ve gerçek emir yok.",
    }


@router.post("/bootstrap")
async def v22_bootstrap(payload: BootstrapRequest, request: Request):
    rt = runtime(request)
    host = request.client.host if request.client else ""
    if not bootstrap_access_allowed(
        host,
        web_owner_authenticated=bool(getattr(request.state, "web_owner_authenticated", False)),
    ):
        raise HTTPException(403, "İlk yönetici yalnızca yerel uygulamadan veya doğrulanmış güvenli web oturumundan oluşturulabilir")
    async with rt["lock"]:
        state = rt["state"]
        if state.get("owner_user_id"):
            raise HTTPException(409, "İlk yönetici daha önce oluşturuldu")
        email = normalize_email(payload.email)
        if "@" not in email:
            raise HTTPException(422, "Geçerli bir e-posta yazın")
        user_id = uuid.uuid4().hex
        user = {
            "id": user_id,
            "email": email,
            "display_name": payload.display_name.strip(),
            "role": "OWNER",
            "active": True,
            "auth_version": 1,
            "password": hash_password(payload.password),
            "created_at": now_iso(),
        }
        state["users"].append(user)
        state["owner_user_id"] = user_id
        expires_at = (datetime.now(timezone.utc) + timedelta(days=3650)).isoformat()
        state["licenses"].append({"id": uuid.uuid4().hex, "user_id": user_id, "plan": "ELITE", "status": "ACTIVE", "starts_at": now_iso(), "expires_at": expires_at, "source": "OWNER_BOOTSTRAP", "demo_only": True})
        add_audit(state, "OWNER_CREATED", "Yerel V24 sahibi ve geliştirme lisansı oluşturuldu.", actor=user_id, subject=user_id)
        save_state(state)
    await persist_v22_commercial(request.app)
    token = issue_token(
        user_id,
        "OWNER",
        rt["secret"],
        token_version=user["auth_version"],
        ttl_seconds=REMEMBER_SESSION_SECONDS if payload.remember else STANDARD_SESSION_SECONDS,
    )
    return {"token": token, "user": public_user(user), "license": active_license(state, user_id), "demo_only": True}


@router.post("/auth/login")
async def v22_login(payload: LoginRequest, request: Request):
    rt = runtime(request)
    host = request.client.host if request.client else "unknown"
    now = time.monotonic()
    attempts = [stamp for stamp in LOGIN_ATTEMPTS.get(host, []) if now - stamp < 300]
    if len(attempts) >= 8:
        raise HTTPException(429, "Çok fazla deneme; beş dakika sonra tekrar deneyin")
    user = next((item for item in rt["state"]["users"] if item.get("email") == normalize_email(payload.email)), None)
    if not user or not user.get("active") or not verify_password(payload.password, user.get("password", {})):
        attempts.append(now)
        LOGIN_ATTEMPTS[host] = attempts
        raise HTTPException(401, "E-posta veya parola hatalı")
    LOGIN_ATTEMPTS.pop(host, None)
    token = issue_token(
        user["id"],
        user["role"],
        rt["secret"],
        token_version=int(user.get("auth_version", 1)),
        ttl_seconds=REMEMBER_SESSION_SECONDS if payload.remember else STANDARD_SESSION_SECONDS,
    )
    return {"token": token, "user": public_user(user), "license": active_license(rt["state"], user["id"]), "demo_only": True}


@router.get("/session")
async def v22_session(request: Request):
    user = authenticated_user(request)
    return {"user": public_user(user), "license": active_license(runtime(request)["state"], user["id"]), "demo_only": True}


@router.get("/admin/overview")
async def v22_admin_overview(request: Request):
    authenticated_user(request, owner=True)
    return admin_overview(runtime(request)["state"])


@router.get("/operations")
async def v22_operations(request: Request):
    authenticated_user(request)
    return operations_overview(request.app)


@router.post("/auth/change-password")
async def v22_change_password(payload: PasswordChangeRequest, request: Request):
    user = authenticated_user(request)
    rt = runtime(request)
    if not verify_password(payload.current_password, user.get("password", {})):
        raise HTTPException(401, "Mevcut parola hatalı")
    async with rt["lock"]:
        user["password"] = hash_password(payload.new_password)
        user["auth_version"] = int(user.get("auth_version", 1)) + 1
        add_audit(rt["state"], "PASSWORD_CHANGED", "Hesap parolası değiştirildi; eski oturumlar kapatıldı.", actor=user["id"], subject=user["id"])
        save_state(rt["state"])
    return {"ok": True, "reauthenticate": True, "message": "Parola değişti. Güvenlik için yeniden giriş yapın."}


@router.post("/customers")
async def v22_create_customer(payload: CustomerRequest, request: Request):
    owner = authenticated_user(request, owner=True)
    rt = runtime(request)
    async with rt["lock"]:
        state = rt["state"]
        email = normalize_email(payload.email)
        if "@" not in email:
            raise HTTPException(422, "Geçerli bir e-posta yazın")
        if any(item.get("email") == email for item in state["users"]):
            raise HTTPException(409, "Bu e-posta zaten kayıtlı")
        user_id = uuid.uuid4().hex
        user = {"id": user_id, "email": email, "display_name": payload.display_name.strip(), "role": "CUSTOMER", "active": True, "auth_version": 1, "password": hash_password(payload.password), "created_at": now_iso()}
        state["users"].append(user)
        expires_at = (datetime.now(timezone.utc) + timedelta(days=payload.days)).isoformat()
        license_row = {"id": uuid.uuid4().hex, "user_id": user_id, "plan": payload.plan, "status": "ACTIVE", "starts_at": now_iso(), "expires_at": expires_at, "source": "MANUAL_DEMO", "demo_only": True}
        state["licenses"].append(license_row)
        state["subscriptions"].append({"id": uuid.uuid4().hex, "user_id": user_id, "plan": payload.plan, "status": "TEST_ACTIVE", "period_end": expires_at, "provider": "MANUAL_DEMO", "created_at": now_iso()})
        add_audit(state, "CUSTOMER_CREATED", f"{email} için {payload.plan} Demo lisansı oluşturuldu.", actor=owner["id"], subject=user_id)
        save_state(state)
    return {"user": public_user(user), "license": license_row, "demo_only": True}


@router.post("/customers/{user_id}/status")
async def v22_customer_status(user_id: str, payload: CustomerStatusRequest, request: Request):
    owner = authenticated_user(request, owner=True)
    rt = runtime(request)
    async with rt["lock"]:
        user = next((item for item in rt["state"]["users"] if item.get("id") == user_id), None)
        if not user:
            raise HTTPException(404, "Kullanıcı bulunamadı")
        if user.get("role") == "OWNER":
            raise HTTPException(409, "Sahip hesabı bu ekrandan askıya alınamaz")
        user["active"] = payload.active
        user["auth_version"] = int(user.get("auth_version", 1)) + 1
        if not payload.active:
            for agent in rt["state"]["agents"]:
                if agent.get("user_id") == user_id and agent.get("status") == "ACTIVE":
                    agent["status"] = "REVOKED"
                    agent["revoked_at"] = now_iso()
                    agent["token_version"] = int(agent.get("token_version", 1)) + 1
        kind = "CUSTOMER_ACTIVATED" if payload.active else "CUSTOMER_SUSPENDED"
        message = f"{user['email']} {'etkinleştirildi' if payload.active else 'askıya alındı'}: {payload.reason}"
        add_audit(rt["state"], kind, message, actor=owner["id"], subject=user_id)
        save_state(rt["state"])
    return {"user": public_user(user), "agents_revoked": not payload.active, "demo_only": True}


@router.post("/subscriptions/activate-demo")
async def v22_activate_subscription(payload: SubscriptionRequest, request: Request):
    owner = authenticated_user(request, owner=True)
    rt = runtime(request)
    async with rt["lock"]:
        state = rt["state"]
        if not any(item.get("id") == payload.user_id for item in state["users"]):
            raise HTTPException(404, "Kullanıcı bulunamadı")
        expires_at = (datetime.now(timezone.utc) + timedelta(days=payload.days)).isoformat()
        row = {"id": uuid.uuid4().hex, "user_id": payload.user_id, "plan": payload.plan, "status": "ACTIVE", "starts_at": now_iso(), "expires_at": expires_at, "source": "MANUAL_DEMO", "demo_only": True}
        state["licenses"].append(row)
        state["subscriptions"].append({"id": uuid.uuid4().hex, "user_id": payload.user_id, "plan": payload.plan, "status": "TEST_ACTIVE", "period_end": expires_at, "provider": "MANUAL_DEMO", "created_at": now_iso()})
        add_audit(state, "LICENSE_ACTIVATED", f"{payload.plan} Demo lisansı {payload.days} gün etkinleştirildi.", actor=owner["id"], subject=payload.user_id)
        save_state(state)
    return {"license": row, "billing_live": False, "demo_only": True}


@router.post("/licenses/{license_id}/revoke")
async def v22_revoke_license(license_id: str, payload: RevokeRequest, request: Request):
    if payload.confirmation.strip().upper() != "LİSANS İPTAL":
        raise HTTPException(422, "İşlem için LİSANS İPTAL yazın")
    owner = authenticated_user(request, owner=True)
    rt = runtime(request)
    async with rt["lock"]:
        row = next((item for item in rt["state"]["licenses"] if item.get("id") == license_id), None)
        if not row:
            raise HTTPException(404, "Lisans bulunamadı")
        target = next((item for item in rt["state"]["users"] if item.get("id") == row.get("user_id")), None)
        if target and target.get("role") == "OWNER":
            raise HTTPException(409, "Sahip geliştirme lisansı iptal edilemez")
        row.update({"status": "REVOKED", "revoked_at": now_iso(), "revoked_reason": payload.reason})
        for subscription in rt["state"]["subscriptions"]:
            if subscription.get("user_id") == row.get("user_id") and subscription.get("status") == "TEST_ACTIVE":
                subscription["status"] = "TEST_CANCELLED"
        for agent in rt["state"]["agents"]:
            if agent.get("user_id") == row.get("user_id") and agent.get("status") == "ACTIVE":
                agent["status"] = "REVOKED"
                agent["revoked_at"] = now_iso()
                agent["token_version"] = int(agent.get("token_version", 1)) + 1
        add_audit(rt["state"], "LICENSE_REVOKED", f"Demo lisansı iptal edildi: {payload.reason}", actor=owner["id"], subject=row.get("user_id"))
        save_state(rt["state"])
    return {"ok": True, "license_id": license_id, "agents_revoked": True, "demo_only": True}


@router.put("/plans/{plan_code}")
async def v22_update_plan(plan_code: str, payload: PlanUpdateRequest, request: Request):
    owner = authenticated_user(request, owner=True)
    rt = runtime(request)
    code = plan_code.upper()
    async with rt["lock"]:
        if code not in rt["state"]["plans"]:
            raise HTTPException(404, "Paket bulunamadı")
        rt["state"]["plans"][code].update({"monthly_usd": payload.monthly_usd, "agents": payload.agents, "bots": payload.bots})
        add_audit(rt["state"], "PLAN_UPDATED", f"{code} fiyatı ve sınırları güncellendi.", actor=owner["id"], subject=code)
        save_state(rt["state"])
    return {"code": code, **rt["state"]["plans"][code], "billing_live": False}


@router.post("/agent/pair-code")
async def v22_pair_code(request: Request):
    user = authenticated_user(request)
    rt = runtime(request)
    license_row = active_license(rt["state"], user["id"])
    if not license_row:
        raise HTTPException(403, "Etkin lisans gerekli")
    raw = f"{secrets.token_hex(4).upper()}-{secrets.token_hex(4).upper()}"
    async with rt["lock"]:
        rt["state"]["pairing_codes"] = [item for item in rt["state"]["pairing_codes"] if parse_date(item.get("expires_at")) > datetime.now(timezone.utc) and not item.get("used")]
        rt["state"]["pairing_codes"].append({"id": uuid.uuid4().hex, "user_id": user["id"], "code_hash": pairing_code_hash(raw, rt["secret"]), "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(), "used": False, "created_at": now_iso()})
        add_audit(rt["state"], "PAIR_CODE_CREATED", "10 dakikalık yerel ajan eşleştirme kodu üretildi.", actor=user["id"], subject=user["id"])
        save_state(rt["state"])
    return {"code": raw, "expires_in_seconds": 600, "message": "Bu kod yalnızca yerel V24 ajanına yazılır; API anahtarı değildir.", "demo_only": True}


@router.post("/agent/pair")
async def v22_pair_agent(payload: PairAgentRequest, request: Request):
    rt = runtime(request)
    code_hash = pairing_code_hash(payload.code, rt["secret"])
    async with rt["lock"]:
        state = rt["state"]
        code = next((item for item in state["pairing_codes"] if item.get("code_hash") == code_hash and not item.get("used") and parse_date(item.get("expires_at")) > datetime.now(timezone.utc)), None)
        if not code:
            raise HTTPException(401, "Eşleştirme kodu geçersiz veya süresi doldu")
        license_row = active_license(state, code["user_id"])
        if not license_row:
            raise HTTPException(403, "Etkin lisans bulunamadı")
        plan = state["plans"].get(license_row["plan"], {})
        active_agents = [item for item in state["agents"] if item.get("user_id") == code["user_id"] and item.get("status") == "ACTIVE"]
        fingerprint_hash = device_fingerprint_hash(payload.fingerprint)
        existing = next((item for item in active_agents if item.get("fingerprint_hash") == fingerprint_hash), None)
        if not existing and len(active_agents) >= int(plan.get("agents", 1)):
            raise HTTPException(409, "Paketin cihaz sınırına ulaşıldı")
        agent = existing or {"id": uuid.uuid4().hex, "user_id": code["user_id"], "fingerprint_hash": fingerprint_hash, "created_at": now_iso(), "token_version": 1}
        if existing:
            agent["token_version"] = int(agent.get("token_version", 1)) + 1
        agent.update({"device_name": payload.device_name.strip(), "status": "ACTIVE", "last_seen_at": now_iso(), "app_version": V22_VERSION, "mode": "DEMO_ONLY"})
        if not existing:
            state["agents"].append(agent)
        code["used"] = True
        add_audit(state, "AGENT_PAIRED", f"{agent['device_name']} güvenli yerel ajan olarak eşleştirildi.", actor=agent["id"], subject=code["user_id"])
        save_state(state)
    token = issue_token(
        agent["id"], "AGENT", rt["secret"], kind="AGENT",
        ttl_seconds=30 * 24 * 60 * 60, token_version=int(agent.get("token_version", 1)),
    )
    return {"agent": agent, "agent_token": token, "commands": [], "mode": "DEMO_ONLY", "exchange_credentials_received": False}


@router.post("/agent/heartbeat")
async def v22_agent_heartbeat(payload: HeartbeatRequest, request: Request):
    rt = runtime(request)
    try:
        token = verify_token(bearer(request), rt["secret"], expected_kind="AGENT")
    except ValueError as exc:
        raise HTTPException(401, str(exc)) from exc
    async with rt["lock"]:
        agent = next((item for item in rt["state"]["agents"] if item.get("id") == token["sub"] and item.get("status") == "ACTIVE"), None)
        if not agent:
            raise HTTPException(401, "Ajan etkin değil")
        if int(token.get("ver", 1)) != int(agent.get("token_version", 1)):
            raise HTTPException(401, "Ajan oturumu yenilenmeli")
        if not active_license(rt["state"], agent["user_id"]):
            raise HTTPException(403, "Lisans süresi doldu")
        agent.update({"last_seen_at": now_iso(), "app_version": payload.app_version, "runtime_status": payload.status, "mode": "DEMO_ONLY"})
        save_state(rt["state"])
    return {"accepted": True, "server_time": now_iso(), "commands": [], "mode": "DEMO_ONLY", "real_orders_enabled": False}


@router.post("/agents/{agent_id}/revoke")
async def v22_revoke_agent(agent_id: str, payload: RevokeRequest, request: Request):
    if payload.confirmation.strip().upper() != "AJAN İPTAL":
        raise HTTPException(422, "İşlem için AJAN İPTAL yazın")
    user = authenticated_user(request)
    rt = runtime(request)
    async with rt["lock"]:
        agent = next((item for item in rt["state"]["agents"] if item.get("id") == agent_id), None)
        if not agent:
            raise HTTPException(404, "Ajan bulunamadı")
        if user.get("role") != "OWNER" and agent.get("user_id") != user.get("id"):
            raise HTTPException(403, "Bu cihaz için yetkiniz yok")
        agent.update({
            "status": "REVOKED", "revoked_at": now_iso(), "revoked_reason": payload.reason,
            "token_version": int(agent.get("token_version", 1)) + 1,
        })
        add_audit(rt["state"], "AGENT_REVOKED", f"{agent.get('device_name', 'Cihaz')} erişimi kaldırıldı: {payload.reason}", actor=user["id"], subject=agent.get("user_id"))
        save_state(rt["state"])
    return {"ok": True, "agent_id": agent_id, "status": "REVOKED", "demo_only": True}


@router.post("/fee-guard")
async def v22_fee_guard(payload: FeeGuardRequest, request: Request):
    authenticated_user(request)
    try:
        return calculate_fee_guard(FeeGuardInput(**payload.model_dump()))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/grid-guard")
async def v22_grid_guard(payload: GridGuardRequest, request: Request):
    authenticated_user(request)
    try:
        return calculate_grid_guard(**payload.model_dump())
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.put("/release-evidence/{evidence_key}")
async def v22_release_evidence(evidence_key: str, payload: ReleaseEvidenceRequest, request: Request):
    owner = authenticated_user(request, owner=True)
    rt = runtime(request)
    key = evidence_key.strip().lower()
    if key not in {"backup", "support", "legal", "security_review"}:
        raise HTTPException(404, "Yayın kanıtı bulunamadı")
    async with rt["lock"]:
        row = rt["state"]["release_evidence"].setdefault(key, {})
        row.update({"status": payload.status, "note": payload.note.strip(), "updated_at": now_iso(), "actor": owner["id"]})
        add_audit(rt["state"], "RELEASE_EVIDENCE", f"{key} kanıt kaydı {payload.status} olarak güncellendi.", actor=owner["id"], subject=key)
        save_state(rt["state"])
    return {"key": key, **row, "self_attested": True, "production_approval": False}


@router.get("/readiness")
async def v22_readiness(request: Request):
    user = authenticated_user(request)
    state = runtime(request)["state"]
    now = datetime.now(timezone.utc)
    online_cutoff = now - timedelta(minutes=3)
    evidence = state.get("release_evidence", {})
    operations = operations_overview(request.app)
    agent_online = any(
        item.get("user_id") == user["id"] and item.get("status") == "ACTIVE"
        and parse_date(item.get("last_seen_at")) >= online_cutoff
        for item in state["agents"]
    )
    gates = [
        {"key": "owner", "label": "Yönetici hesabı", "passed": bool(state.get("owner_user_id")), "detail": "Yerel sahip oluşturuldu."},
        {"key": "auth", "label": "Parola ve imzalı oturum", "passed": True, "detail": "Scrypt parola özeti ve HMAC süreli oturum kullanılıyor."},
        {"key": "license", "label": "Etkin lisans", "passed": bool(active_license(state, user["id"])), "detail": "Plan, bitiş tarihi ve cihaz sınırı doğrulanıyor."},
        {"key": "agent", "label": "Güvenli yerel ajan", "passed": agent_online, "detail": "API anahtarını merkeze göndermeyen, sürekli kalp atışlı cihaz modeli."},
        {"key": "demo_connector", "label": "Binance Futures Demo bağlantısı", "passed": bool(operations["demo_connector"]["configured"]), "detail": "Anahtar yalnızca yerel Windows DPAPI kasasında tutulur."},
        {"key": "fee_guard", "label": "Net kâr koruması", "passed": True, "detail": "Komisyon, kayma ve fonlama tahmini karar öncesi düşülüyor."},
        {"key": "backup", "label": "Yedekleme tatbikatı", "passed": evidence.get("backup", {}).get("status") == "RECORDED", "detail": evidence.get("backup", {}).get("note", "YEDEKLE.bat tatbikatı bekleniyor.")},
        {"key": "support", "label": "Müşteri destek süreci", "passed": evidence.get("support", {}).get("status") == "RECORDED", "detail": evidence.get("support", {}).get("note", "Destek akışı bekleniyor.")},
        {"key": "payment", "label": "Canlı ödeme sağlayıcısı", "passed": False, "detail": "Şimdilik MANUAL_DEMO; para tahsilatı kapalı."},
        {"key": "legal", "label": "Hukuk ve sözleşmeler", "passed": False, "detail": evidence.get("legal", {}).get("note", "Satış öncesi ülkeye özel hukuk incelemesi gerekli.")},
        {"key": "security_review", "label": "Bağımsız güvenlik testi", "passed": False, "detail": evidence.get("security_review", {}).get("note", "Genel kullanıma açılmadan pentest ve gizli anahtar yönetimi gerekli.")},
    ]
    passed = sum(1 for item in gates if item["passed"])
    return {
        "version": V22_VERSION,
        "stage": "COMMERCIAL COMPLETE · LAUNCH LAB · DEMO",
        "score": round(passed / len(gates) * 100),
        "passed": passed,
        "total": len(gates),
        "gates": gates,
        "production_ready": False,
        "closed_beta_candidate": all(item["passed"] for item in gates if item["key"] in {"owner", "auth", "license", "agent", "demo_connector", "fee_guard", "backup", "support"}),
        "demo_only": True,
        "release_evidence": evidence,
        "next_step": "Demo emir, otomasyon, yedek ve destek tatbikatlarını tamamla; ardından bağımsız hukuk ve güvenlik incelemesine geç.",
    }


def init_v22_commercial(application: Any) -> None:
    state = load_state()
    application.state.v22_commercial = {
        "state": state,
        "secret": load_secret(),
        "lock": asyncio.Lock(),
        "storage_lock": asyncio.Lock(),
        "storage_ready": False,
        "restore_attempted": False,
        "storage_status": "YEREL_YEDEK",
    }
    add_audit(state, "V24_START", "V24 Commercial Complete başladı; ödeme ve gerçek emir kanalları kapalı.")
    save_state(state)


async def shutdown_v22_commercial(application: Any) -> None:
    if hasattr(application.state, "v22_commercial"):
        save_state(application.state.v22_commercial["state"])
        await persist_v22_commercial(application)
