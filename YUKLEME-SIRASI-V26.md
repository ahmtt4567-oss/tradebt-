# V26 tek seferde yükleme sırası

## A. GitHub

1. ZIP'i bilgisayarınızda çıkartın.
2. Çıkan `ProTreBot-Web-V26-Testnet-First` klasörünün **içindeki** dosyaları özel
   `Gezginci08/ProTreBot-Web` deponuzun köküne yükleyin.
3. Eski dosyaların üzerine yazılmasını onaylayıp tek commit oluşturun.
4. ZIP dosyasının kendisini, `.env`, `node_modules`, `dist` veya API anahtarlarını yüklemeyin.

## B. Render

1. `protrebot-api` servisini açın.
2. **Environment** bölümüne girin.
3. Şimdilik yalnızca şunları ekleyin:
   - `BINANCE_DEMO_API_KEY`
   - `BINANCE_DEMO_SECRET_KEY`
4. `BINANCE_LIVE_API_KEY` ve `BINANCE_LIVE_SECRET_KEY` değerlerini eklemeyin/boş bırakın.
5. **Manual Deploy > Deploy latest commit** seçin.
6. `/api/health` yanıtında `version: 26.0.0`, `paper: DEVRE DIŞI` ve
   `mode: TESTNET_FIRST_WITH_LIVE_READY` değerlerini doğrulayın.

## C. Vercel

1. GitHub commit'i algılanınca otomatik dağıtımı bekleyin.
2. Otomatik başlamazsa **Deployments > Redeploy** seçin.
3. Sayfayı açıp yönetici koduyla giriş yapın.

## D. İlk güvenli kullanım

1. `Yayın Kapıları` sekmesinde Demo anahtarlarının algılandığını görün.
2. `Testnet Komuta` sekmesinde bağlantı testini çalıştırın.
3. Küçük Demo bakiye ve en düşük kaldıraçla emir testi yapın.
4. Pozisyon, Stop ve TP emirlerini Binance Demo sayfasında da doğrulayın.
5. `Canlı Hazırlık` sekmesi görünür olabilir; canlı API olmadığı için kilitli kalmalıdır.

> Daha önce ekran görüntüsünde görünen Demo anahtarını Binance'ten silip yenisini üretin.
