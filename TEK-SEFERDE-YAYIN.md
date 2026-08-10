# ProTreBot V25.1.2 — Tek Seferde Doğru Yayın

Bu dosya, GitHub ana sayfasına dosyaların yanlışlıkla dağılmasını önleyen son yayın yoludur.

## En güvenli yöntem: GitHub Desktop

1. GitHub Desktop uygulamasını açın ve GitHub hesabınızla giriş yapın.
2. **File > Clone repository** seçin.
3. `Gezginci08/ProTreBot-Web` deposunu seçip bilgisayarınıza klonlayın.
4. Bu paketteki `ProTreBot-Web-V1` klasörünü açın.
5. Klasörün içindeki `backend`, `frontend`, `database` klasörleri ile kök dosyaları klonlanan `ProTreBot-Web` klasörüne kopyalayın.
6. Windows sorarsa **Hedefteki dosyaları değiştir** seçeneğini onaylayın.
7. `.env`, API anahtarı, parola, `node_modules`, `dist`, `.venv` veya `backend/data` kopyalamayın.
8. GitHub Desktop'a dönün. Summary alanına `V25.1.2 final stabilizasyon` yazın.
9. **Commit to main**, ardından **Push origin** düğmesine basın.

GitHub sayfasında `backend/app/main.py` ve `frontend/src/App.tsx` yolları görünmelidir. `App.tsx` veya `main.py` yalnızca depo ana sayfasında görünüyorsa yanlış konumdadır.

## Dağıtımın tamamlandığını doğrulama

1. Render dağıtımının **Live** olmasını bekleyin.
2. `https://protrebot-api.onrender.com/api/health` adresini açın.
3. Yanıtta `"version":"25.1.2"` ve `"patch":"25.1.2-json-safe"` görünmelidir.
4. Vercel dağıtımının **Ready** olmasını bekleyin.
5. `https://pro-tre-bot-web.vercel.app` adresini açıp `Ctrl+F5` yapın.
6. Sol üstte `V25.1.2 · LIVE GUARD` görünmelidir.
7. `50 USDT DEMO AÇ` düğmesi sayfayı boşaltmadan Paper pozisyonu açmalıdır.

## Güvenlik sınırı

Bu yayın Paper/demo içindir. Gerçek para veya Testnet emri kendiliğinden açılmaz. Kâr garanti edilmez; stop ile kapanan zarar işlemleri normal risk yönetiminin parçasıdır.
