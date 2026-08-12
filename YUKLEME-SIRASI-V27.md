# V27 tek seferde yükleme sırası

## 1. GitHub

1. ZIP'i bilgisayarınızda çıkarın.
2. `ProTreBot-Web-V27-Cloud-Ops` klasörünün **içindeki** dosyaları özel
   `Gezginci08/ProTreBot-Web` deponuzun köküne yükleyin.
3. Eski dosyaların üzerine yazılmasını onaylayın ve tek commit oluşturun.
4. ZIP, `.env`, `node_modules`, `dist`, `.venv`, API anahtarı veya Secret yüklemeyin.

## 2. Render

1. `protrebot-api` servisini açın.
2. GitHub commit'i algılamadıysa **Manual Deploy > Deploy latest commit** seçin.
3. Mevcut Demo anahtarlarını değiştirmeyin; canlı anahtarları boş bırakın.
4. `/api/health` yanıtında şunları doğrulayın:
   - `version: 27.0.0`
   - `mode: TESTNET_FIRST_CLOUD_DURABLE`
   - `cloud_evidence: KALICI`

## 3. Vercel

1. Otomatik dağıtımı bekleyin; başlamazsa **Deployments > Redeploy** seçin.
2. Root Directory değerinin `frontend` olduğunu değiştirmeyin.
3. Siteyi açın ve mevcut yönetici kodunuzla giriş yapın.

## 4. İlk kontrol

1. **Operasyon & Kanıt** sekmesini açın.
2. `KALICI KANIT` kartında **KALICI** yazısını görün.
3. **Testnet Komuta** bölümünde Demo bağlantısını test edin.
4. Demo emir kilidini açtıktan sonra otomasyonu yalnızca Testnet için başlatın.
5. İşlem açılmasa bile Son Karar alanında bekleme nedenini kontrol edin.

> API/Secret veya yönetici kodunu ekran görüntüsünde ya da sohbet mesajında paylaşmayın.
