# ProTreBot Web V1 — Güvenli Yönetici Önizlemesi

> Güncel bakım paketi: **V1.2 / V25.1.1**. Demo işlem sonrası boş ekran,
> geçici Render 500/502 yanıtları ve arayüz kurtarma koruması eklendi.

Bu paket ilk internet yayını içindir. Tek yönetici erişim koduyla korunur,
Paper işlemleri kullanır ve müşteri parası tutmaz. Gerçek/Testnet emirleri
sunucu ortamına taşınmaz.

## 1. GitHub

1. ZIP'i bilgisayarda çıkartın.
2. `ProTreBot-Web-V1` klasörünün **içindekileri** özel `ProTreBot-Web`
   deposuna yükleyin. ZIP dosyasını tek başına yüklemeyin.
3. `.env`, API anahtarı, `backend/data`, `node_modules` ve `dist` yüklemeyin.

## 2. Render backend

1. Render hesabında **New > Blueprint** seçin.
2. Özel GitHub `ProTreBot-Web` deposunu bağlayın.
3. Render kökteki `render.yaml` dosyasını okuyacaktır.
4. `PROTREBOT_WEB_ACCESS_TOKEN` için en az 24 karakterlik, yalnızca sizin
   bildiğiniz bir kod girin.
5. İlk aşamada `PROTREBOT_CORS_ORIGINS` değerine `http://localhost:5173`
   yazılabilir. Vercel adresi oluştuktan sonra bunu Vercel adresiyle değiştirin.
6. Dağıtım bitince `https://...onrender.com/api/health` adresini kontrol edin.

Ücretsiz Render servisi yalnızca önizleme içindir ve boşta kalınca uyuyabilir.
7/24 bot çalışması için testlerden sonra ücretli, sürekli çalışan plana geçin.

## 3. Vercel frontend

1. Vercel'de **Add New > Project** seçin ve aynı GitHub deposunu bağlayın.
2. Root Directory olarak `frontend` seçin.
3. Environment Variables bölümüne şunları ekleyin:
   - `VITE_API_URL` = Render servis adresi, örn. `https://protrebot-api.onrender.com`
   - `VITE_WEB_ACCESS_REQUIRED` = `true`
4. Deploy düğmesine basın.
5. Oluşan `https://...vercel.app` adresini kopyalayın.
6. Render'da `PROTREBOT_CORS_ORIGINS` değerini bu tam adres yapıp backend'i
   yeniden dağıtın.

## 4. İlk giriş

Vercel adresini açınca görünen yönetici ekranına, Render'da belirlediğiniz
`PROTREBOT_WEB_ACCESS_TOKEN` değerini yazın. Bu kod Binance API anahtarı değildir.

## Güvenlik sınırı

- Binance anahtarları GitHub veya Vercel'e yazılmaz.
- Bu önizleme müşteri üyeliği veya ödeme sistemi değildir.
- Çok kullanıcılı müşteri sürümünden önce kullanıcı izolasyonu, şifreli anahtar
  kasası, abonelik ve denetim kayıtları ayrıca tamamlanmalıdır.
