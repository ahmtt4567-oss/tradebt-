# ProTreBot V27 — Tek Seferde Doğru Yayın

## GitHub

1. GitHub Desktop ile özel `Gezginci08/ProTreBot-Web` deposunu klonlayın.
2. Bu paketteki `ProTreBot-Web-V27-Cloud-Ops` klasörünün **içindeki** dosyaları klonlanan
   deponun köküne kopyalayın.
3. Windows sorarsa hedefteki dosyaları değiştirin.
4. `.env`, API anahtarı, parola, `node_modules`, `dist`, `.venv` ve çalışma verisi kopyalamayın.
5. `V27 cloud operations` açıklamasıyla commit ve push yapın.

## Render

1. GitHub push sonrasında dağıtım başlamazsa **Manual Deploy > Deploy latest commit** seçin.
2. `https://protrebot-api.onrender.com/api/health` adresinde şunları görün:
   - `version: 27.0.0`
   - `mode: TESTNET_FIRST_CLOUD_DURABLE`
   - `cloud_evidence: KALICI`

## Vercel

1. Vercel otomatik dağıtımı tamamladığında siteyi açıp `Ctrl+F5` yapın.
2. Sol üstte `V27 · CLOUD OPERATIONS / TESTNET-FIRST` görünmelidir.
3. **Operasyon & Kanıt** sekmesini açıp kalıcı kanıt durumunu kontrol edin.

## Güvenlik sınırı

İlk yayında yalnızca Binance Futures Demo anahtarlarını kullanın. Anahtarları GitHub'a,
Vercel'e, ekran görüntüsüne veya sohbete koymayın. Testnet kâr garantisi vermez ve ücretsiz
sunucu katmanı 7/24 otomasyon sağlamaz.
