"""Windows-only local credential vault for Binance Demo keys.

The encrypted blob is bound to the current Windows user through DPAPI.  Other
platforms intentionally return no data so development and tests never create a
plain-text secret by accident.
"""

from __future__ import annotations

import ctypes
import json
import os
from ctypes import wintypes

from .local_storage import DATA_DIR, migrate_legacy_files


migrate_legacy_files((
    "demo_credentials.dat", "v22_agent_token.dat", "live_credentials.dat", "live_consent.dat",
))
VAULT_PATH = DATA_DIR / "demo_credentials.dat"
AGENT_VAULT_PATH = DATA_DIR / "v22_agent_token.dat"
LIVE_VAULT_PATH = DATA_DIR / "live_credentials.dat"
LIVE_CONSENT_PATH = DATA_DIR / "live_consent.dat"


class DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]


def _blob(data: bytes) -> tuple[DATA_BLOB, ctypes.Array]:
    buffer = ctypes.create_string_buffer(data)
    return DATA_BLOB(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte))), buffer


def _protect(data: bytes) -> bytes:
    if os.name != "nt":
        raise RuntimeError("DPAPI yalnızca Windows üzerinde kullanılabilir.")
    source, keepalive = _blob(data)
    output = DATA_BLOB()
    if not ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(source), "ProTreBot Binance Demo", None, None, None, 0,
        ctypes.byref(output),
    ):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(output.pbData, output.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(output.pbData)
        del keepalive


def _unprotect(data: bytes) -> bytes:
    if os.name != "nt":
        return b""
    source, keepalive = _blob(data)
    output = DATA_BLOB()
    if not ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(source), None, None, None, None, 0, ctypes.byref(output),
    ):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(output.pbData, output.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(output.pbData)
        del keepalive


def save_credentials(api_key: str, secret_key: str) -> None:
    payload = json.dumps({"api_key": api_key.strip(), "secret_key": secret_key.strip()}).encode("utf-8")
    encrypted = _protect(payload)
    VAULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = VAULT_PATH.with_suffix(".tmp")
    temporary.write_bytes(encrypted)
    temporary.replace(VAULT_PATH)


def load_credentials() -> tuple[str, str]:
    if os.name != "nt" or not VAULT_PATH.exists():
        return "", ""
    try:
        payload = json.loads(_unprotect(VAULT_PATH.read_bytes()).decode("utf-8"))
        return str(payload.get("api_key") or "").strip(), str(payload.get("secret_key") or "").strip()
    except (OSError, ValueError, UnicodeError):
        return "", ""


def delete_credentials() -> None:
    try:
        VAULT_PATH.unlink()
    except FileNotFoundError:
        pass


def save_agent_token(agent_token: str, agent_id: str) -> None:
    """Bind the V22 license token to the current Windows user with DPAPI."""
    payload = json.dumps({"agent_token": agent_token.strip(), "agent_id": agent_id.strip()}).encode("utf-8")
    encrypted = _protect(payload)
    AGENT_VAULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = AGENT_VAULT_PATH.with_suffix(".tmp")
    temporary.write_bytes(encrypted)
    temporary.replace(AGENT_VAULT_PATH)


def load_agent_token() -> tuple[str, str]:
    if os.name != "nt" or not AGENT_VAULT_PATH.exists():
        return "", ""
    try:
        payload = json.loads(_unprotect(AGENT_VAULT_PATH.read_bytes()).decode("utf-8"))
        return str(payload.get("agent_token") or "").strip(), str(payload.get("agent_id") or "").strip()
    except (OSError, ValueError, UnicodeError):
        return "", ""


def _atomic_protected_json(path, payload: dict) -> None:
    encrypted = _protect(json.dumps(payload).encode("utf-8"))
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_bytes(encrypted)
    temporary.replace(path)


def _load_protected_json(path) -> dict:
    if os.name != "nt" or not path.exists():
        return {}
    try:
        payload = json.loads(_unprotect(path.read_bytes()).decode("utf-8"))
        return payload if isinstance(payload, dict) else {}
    except (OSError, ValueError, UnicodeError):
        return {}


def save_live_credentials(api_key: str, secret_key: str) -> None:
    """Store live USD-M Futures credentials separately from Demo credentials."""
    _atomic_protected_json(LIVE_VAULT_PATH, {
        "api_key": api_key.strip(),
        "secret_key": secret_key.strip(),
        "scope": "BINANCE_USDM_FUTURES_LIVE",
    })


def load_live_credentials() -> tuple[str, str]:
    """Load live credentials without ever exposing them to the browser.

    Hosted V28 deployments prefer the encrypted in-application PostgreSQL
    vault. Legacy Render variables remain a migration-only fallback, while
    the Windows DPAPI vault remains available for the desktop build. A
    partially configured source fails closed instead of silently falling
    back to a different credential set.
    """
    try:
        from .exchange_connections import cached_credentials, vault_managed

        vault_values = cached_credentials("LIVE", active_only=True)
        if vault_values[0] and vault_values[1]:
            return vault_values
        if vault_managed("LIVE"):
            return "", ""
    except (ImportError, RuntimeError, ValueError):
        pass
    env_api_key = os.getenv("BINANCE_LIVE_API_KEY", "").strip()
    env_secret_key = os.getenv("BINANCE_LIVE_SECRET_KEY", "").strip()
    if env_api_key or env_secret_key:
        if len(env_api_key) >= 10 and len(env_secret_key) >= 10:
            return env_api_key, env_secret_key
        return "", ""
    payload = _load_protected_json(LIVE_VAULT_PATH)
    if payload.get("scope") != "BINANCE_USDM_FUTURES_LIVE":
        return "", ""
    return str(payload.get("api_key") or "").strip(), str(payload.get("secret_key") or "").strip()


def live_credential_source() -> str:
    """Return a public storage label, never credential material."""
    try:
        from .exchange_connections import credential_source, vault_managed

        if vault_managed("LIVE"):
            return credential_source("LIVE")
    except (ImportError, RuntimeError, ValueError):
        pass
    env_api_key = os.getenv("BINANCE_LIVE_API_KEY", "").strip()
    env_secret_key = os.getenv("BINANCE_LIVE_SECRET_KEY", "").strip()
    if env_api_key or env_secret_key:
        return "RENDER_ENV" if len(env_api_key) >= 10 and len(env_secret_key) >= 10 else "RENDER_ENV_EKSİK"
    if os.name == "nt" and LIVE_VAULT_PATH.exists():
        return "WINDOWS_DPAPI"
    return "YAPILANDIRILMADI"


def delete_live_credentials() -> None:
    try:
        LIVE_VAULT_PATH.unlink()
    except FileNotFoundError:
        pass


def save_live_consent(*, accepted_at: str, expires_at_epoch: float, key_fingerprint: str) -> None:
    """Bind a short local live-execution consent to this Windows user and key."""
    _atomic_protected_json(LIVE_CONSENT_PATH, {
        "accepted_at": accepted_at,
        "expires_at_epoch": float(expires_at_epoch),
        "key_fingerprint": key_fingerprint,
        "scope": "PROTREBOT_V25_LIVE_EXECUTION_CONSENT",
    })


def load_live_consent() -> dict:
    payload = _load_protected_json(LIVE_CONSENT_PATH)
    return payload if payload.get("scope") == "PROTREBOT_V25_LIVE_EXECUTION_CONSENT" else {}


def delete_live_consent() -> None:
    try:
        LIVE_CONSENT_PATH.unlink()
    except FileNotFoundError:
        pass
