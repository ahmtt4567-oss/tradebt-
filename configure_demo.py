"""Local-only Binance Futures Demo credential setup with a masked GUI."""

from __future__ import annotations

import getpass
import os
from pathlib import Path


ENV_PATH = Path(__file__).resolve().parent / ".env"
KEY_NAMES = ("BINANCE_DEMO_API_KEY", "BINANCE_DEMO_SECRET_KEY")


def valid_secret(value: str) -> bool:
    return len(value) >= 10 and not any(character.isspace() for character in value)


def update_env(api_key: str, secret_key: str) -> None:
    existing = ENV_PATH.read_text(encoding="utf-8").splitlines() if ENV_PATH.exists() else []
    kept = [line for line in existing if not any(line.startswith(f"{name}=") for name in KEY_NAMES)]
    kept.extend([
        f"BINANCE_DEMO_API_KEY={api_key}",
        f"BINANCE_DEMO_SECRET_KEY={secret_key}",
    ])
    temporary = ENV_PATH.with_suffix(".env.tmp")
    temporary.write_text("\n".join(kept).rstrip() + "\n", encoding="utf-8")
    os.replace(temporary, ENV_PATH)
    try:
        os.chmod(ENV_PATH, 0o600)
    except OSError:
        pass


def save_local(api_key: str, secret_key: str) -> str:
    """Prefer the current Windows user's encrypted DPAPI vault."""
    if os.name == "nt":
        try:
            from app.credential_store import save_credentials

            save_credentials(api_key, secret_key)
            if ENV_PATH.exists():
                kept = [
                    line for line in ENV_PATH.read_text(encoding="utf-8").splitlines()
                    if not any(line.startswith(f"{name}=") for name in KEY_NAMES)
                ]
                ENV_PATH.write_text("\n".join(kept).rstrip() + ("\n" if kept else ""), encoding="utf-8")
            return "Windows kullanıcı kasasına (DPAPI)"
        except (ImportError, OSError, RuntimeError):
            pass
    update_env(api_key, secret_key)
    return "backend/.env dosyasına"


def console_main() -> int:
    print("=" * 62)
    print(" PROTREBOT V21 - BINANCE FUTURES DEMO ANAHTAR AYARI")
    print("=" * 62)
    print("Bu ekran yalnızca bilgisayarınızda çalışır.")
    print("Anahtarları ChatGPT'ye, bir mesaja veya ekran görüntüsüne koymayın.\n")
    api_key = getpass.getpass("Demo API Key (yazarken görünmez): ").strip()
    secret_key = getpass.getpass("Demo Secret Key (yazarken görünmez): ").strip()
    if not valid_secret(api_key) or not valid_secret(secret_key):
        print("\nHATA: Anahtarlar boş, çok kısa veya boşluk içeriyor.")
        return 1
    location = save_local(api_key, secret_key)
    print(f"\nTAMAM: Anahtarlar {location} yerel olarak kaydedildi.")
    print("ProTreBot açıksa DURDUR.bat, ardından BASLAT.bat çalıştırın.")
    return 0


def gui_main() -> int:
    import tkinter as tk
    from tkinter import messagebox

    result = {"code": 1}
    root = tk.Tk()
    root.title("ProTreBot V21 · Binance Futures Demo Anahtar Ayarı")
    root.geometry("660x430")
    root.resizable(False, False)
    root.configure(bg="#f6f9e9")

    title = tk.Label(root, text="BINANCE FUTURES DEMO ANAHTAR AYARI", bg="#f6f9e9", fg="#174c2e", font=("Segoe UI", 16, "bold"))
    title.pack(pady=(25, 5))
    note = tk.Label(root, text="Anahtarlar bu Windows kullanıcısına bağlı şifreli kasada saklanır.\nSohbete veya ekran görüntüsüne koymayın.", bg="#f6f9e9", fg="#64725d", font=("Segoe UI", 10), justify="center")
    note.pack(pady=(0, 20))

    panel = tk.Frame(root, bg="#ffffff", highlightbackground="#cddda5", highlightthickness=1, padx=22, pady=18)
    panel.pack(fill="x", padx=38)
    api_var = tk.StringVar()
    secret_var = tk.StringVar()

    def paste_into(variable: tk.StringVar) -> None:
        try:
            variable.set(root.clipboard_get().strip())
        except tk.TclError:
            messagebox.showwarning("Pano boş", "Önce Binance sayfasındaki anahtarı kopyalayın.", parent=root)

    def add_field(label: str, variable: tk.StringVar, row: int) -> None:
        tk.Label(panel, text=label, bg="#ffffff", fg="#31583b", font=("Segoe UI", 9, "bold")).grid(row=row, column=0, sticky="w", pady=(0, 5))
        entry = tk.Entry(panel, textvariable=variable, show="*", font=("Consolas", 10), relief="solid", bd=1)
        entry.grid(row=row + 1, column=0, sticky="ew", ipady=8, pady=(0, 14))
        tk.Button(panel, text="PANODAN YAPIŞTIR", command=lambda: paste_into(variable), bg="#e7f48b", fg="#245334", relief="flat", font=("Segoe UI", 8, "bold"), padx=12, pady=7).grid(row=row + 1, column=1, padx=(10, 0), sticky="n")

    panel.columnconfigure(0, weight=1)
    add_field("DEMO API KEY", api_var, 0)
    add_field("DEMO SECRET KEY", secret_var, 2)

    def save() -> None:
        api_key = api_var.get().strip()
        secret_key = secret_var.get().strip()
        if not valid_secret(api_key) or not valid_secret(secret_key):
            messagebox.showerror("Geçersiz anahtar", "İki alanı da Panodan Yapıştır düğmesiyle doldurun. Anahtarlarda boşluk bulunmamalı.", parent=root)
            return
        location = save_local(api_key, secret_key)
        result["code"] = 0
        messagebox.showinfo("Tamamlandı", f"Demo anahtarları {location} kaydedildi.\nŞimdi DURDUR.bat ve ardından BASLAT.bat çalıştırın.", parent=root)
        root.destroy()

    tk.Button(root, text="GÜVENLİ BİÇİMDE KAYDET", command=save, bg="#159653", fg="#ffffff", activebackground="#117a44", activeforeground="#ffffff", relief="flat", font=("Segoe UI", 10, "bold"), padx=24, pady=12).pack(pady=20)
    root.mainloop()
    return result["code"]


def main() -> int:
    try:
        return gui_main()
    except (ImportError, RuntimeError):
        return console_main()


if __name__ == "__main__":
    raise SystemExit(main())
