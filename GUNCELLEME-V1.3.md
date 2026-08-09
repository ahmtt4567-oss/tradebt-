# V1.3 / V25.1.2 — Render 500 ve Demo Ekran Koruması

Bu paket V1.2'nin tamamını içerir. Ayrı eski paketleri sırayla kurmanız gerekmez.

## Düzeltilenler

- Risk Lab içindeki `NaN` ve `Infinity` değerleri API yanıtından önce temizlenir.
- `/api/v11/risk-lab` artık JSON serileştirme sırasında kontrolsüz 500 üretmez.
- Sağlık yanıtına `25.1.2-json-safe` dağıtım işareti eklendi.
- Demo düğmeleri açıkça `button` türüne alındı; istemsiz sayfa gönderimi engellendi.
- API'nin nesne biçimindeki hata ayrıntıları `[object Object]` yerine okunur mesaja çevrilir.
- Önceki Paper hesap doğrulaması ve boş ekran kurtarma koruması korunur.

## Kurulum

1. ZIP'i çıkarın.
2. `ProTreBot-Web-V1` klasörünün **içindeki** her şeyi GitHub deposunun köküne yükleyin.
3. `.env`, API anahtarı, parola veya yerel veri dosyası yüklemeyin.
4. GitHub değişikliğini commit edin.
5. Render `Live`, Vercel `Ready` olduktan sonra tarayıcıda `Ctrl+F5` yapın.

Render ayarları:

- Root Directory: `backend`
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

Vercel Root Directory: `frontend`

## Güvenlik

Bu hotfix gerçek veya Testnet borsa emri açmaz. `50 USDT DEMO AÇ` yalnızca Paper simülasyonudur.
