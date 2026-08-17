# V28 Borsa Bağlantıları — Teknik Not

## Uçlar

- `GET /api/exchange-connections/status`
- `POST /api/exchange-connections/test`
- `POST /api/exchange-connections/save`
- `POST /api/exchange-connections/activate`
- `POST /api/exchange-connections/deactivate`
- `DELETE /api/exchange-connections/credentials`

Tüm uçlar mevcut yönetici erişim kapısıyla korunur. Test ve aktivasyon yalnızca Binance
USD-M Futures `GET /fapi/v3/account` ve `GET /fapi/v1/positionSide/dual` çağrılarını yapar;
emir uçlarına çağrı yapmaz.

## Saklama

- Tablo: `protrebot_exchange_vault`
- Şifreleme: Fernet (AES-128-CBC + HMAC-SHA256 doğrulamalı token)
- Anahtar türetme: `PROTREBOT_VAULT_MASTER_KEY`, yoksa mevcut
  `PROTREBOT_WEB_ACCESS_TOKEN`
- Veritabanında: şifreli payload, geri döndürülemez fingerprint, bağlantı durumu ve anahtarsız
  hesap özeti
- API yanıtında: Secret veya API Key yok

## Fail-closed davranış

- PostgreSQL veya kasa anahtarı hazır değilse yeni bağlantı kurulamaz.
- Kasa kaydı pasifse eski ortam değişkeni aynı kanalı gizlice açamaz.
- Anahtar değişimi Testnet/Canlı emir kilitlerini sıfırlar.
- Canlı bağlantı aktivasyonu V25 emir kilidini açmaz.
- Aktif bağlantı kapatılmadan anahtar silinemez.
- Görünen açık pozisyon varken anahtar silme reddedilir.

