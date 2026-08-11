"""V25 local license agent with continuous heartbeat.

It stores only a license-agent token with Windows DPAPI. It never asks for,
reads or sends an exchange API key.
"""

from __future__ import annotations

import json
import platform
import socket
import sys
import time
import urllib.error
import urllib.request
import uuid

from app.credential_store import load_agent_token, save_agent_token


API = "http://127.0.0.1:8000/api/v22"
APP_VERSION = "25.1.2"
HEARTBEAT_SECONDS = 45


def post(path: str, payload: dict, token: str = "") -> dict:
    body = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(f"{API}{path}", data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            detail = json.loads(exc.read().decode("utf-8")).get("detail")
        except (ValueError, UnicodeError):
            detail = None
        raise RuntimeError(str(detail or f"HTTP {exc.code}")) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError("V22 API çalışmıyor. Önce BASLAT.bat dosyasını açın.") from exc


def fingerprint() -> str:
    return "|".join([
        platform.system(), platform.release(), platform.machine(), platform.processor() or "cpu",
        socket.gethostname(), f"{uuid.getnode():012x}",
    ])


def monitor(token: str, agent_id: str, device_name: str = "Bu cihaz") -> None:
    print(f"\nAKTİF: {device_name} lisans ajanı çevrimiçi ({agent_id[:8]}).")
    print(f"Her {HEARTBEAT_SECONDS} saniyede güvenli lisans kalp atışı gönderilir.")
    print("Borsa anahtarı okunmaz veya sunucuya gönderilmez. Durdurmak için CTRL+C.")
    failures = 0
    while True:
        try:
            result = post("/agent/heartbeat", {"app_version": APP_VERSION, "status": "READY"}, token)
            failures = 0
            stamp = result.get("server_time", "")
            print(f"[OK] Kalp atışı kabul edildi · {stamp} · {result.get('mode', 'DEMO_ONLY')}")
        except RuntimeError as exc:
            failures += 1
            print(f"[BEKLE] Kalp atışı {failures}/5: {exc}")
            if failures >= 5:
                raise RuntimeError("Ajan beş kez doğrulanamadı. Paneli ve lisansı kontrol edip yeniden açın.") from exc
        time.sleep(HEARTBEAT_SECONDS)


def main() -> int:
    print("=" * 64)
    print(" PROTREBOT V25.1.2 - GUVENLI YEREL AJAN")
    print(" Yalnizca lisans eslestirir; borsa API anahtari istemez.")
    print("=" * 64)
    token, agent_id = load_agent_token()
    if token:
        try:
            post("/agent/heartbeat", {"app_version": APP_VERSION, "status": "READY"}, token)
            monitor(token, agent_id)
            return 0
        except RuntimeError as exc:
            print(f"\nKayitli ajan dogrulanamadi: {exc}")
    code = input("\nPanelde uretilen 10 dakikalik eslestirme kodu: ").strip()
    device_name = input("Bu cihaza vereceginiz ad: ").strip() or socket.gethostname()
    try:
        result = post("/agent/pair", {"code": code, "device_name": device_name, "fingerprint": fingerprint()})
        agent = result["agent"]
        save_agent_token(result["agent_token"], agent["id"])
        post("/agent/heartbeat", {"app_version": APP_VERSION, "status": "READY"}, result["agent_token"])
        print(f"\nTAMAM: {device_name} guvenli ajan olarak eslesti.")
        print("Token Windows kullaniciniza DPAPI ile sifreli kaydedildi.")
        print("Borsa anahtari alinmadi ve sunucuya gonderilmedi.")
        monitor(result["agent_token"], agent["id"], device_name)
        return 0
    except KeyboardInterrupt:
        print("\nAjan kullanici tarafindan durduruldu. Lisans kaydi korunuyor.")
        return 0
    except (RuntimeError, KeyError) as exc:
        print(f"\nHATA: {exc}")
        input("Kapatmak icin Enter'a basin...")
        return 1


if __name__ == "__main__":
    sys.exit(main())
