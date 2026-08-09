# ProTreBot Web V1.1 — Güvenli İlk Kayıt Düzeltmesi

Bu güncelleme, internet üzerinde çalışan panelde ilk yönetici hesabının
oluşturulamaması sorununu düzeltir.

## Değişiklikler

- İlk sahip kaydı yalnızca doğrulanmış `X-ProTreBot-Owner` web oturumunda açılır.
- Yerel kullanımda `127.0.0.1` desteği korunur.
- İlk sahip hesabı tek sefer oluşturulur; ikinci sahip kaydı engellenir.
- Hesap, lisans ve ticari Demo durumu PostgreSQL içinde kalıcı saklanır.
- Oturum imzası web erişim sırrından alan ayrımlı olarak türetilir; yeniden
  başlatmalarda aynı erişim kodu kullanıldığı sürece kararlı kalır.
- Gerçek para, Testnet ve borsa emri kanalları kapalı kalır.

## Güncelleme

1. ZIP'i bilgisayarınızda çıkarın.
2. Çıkan klasörün **içindeki** dosya ve klasörleri mevcut özel GitHub deposunun
   köküne yükleyin.
3. GitHub değişiklikleri kaydedince Render ve Vercel otomatik olarak yeniden
   yayımlar.
4. Önce Render servisinin `Live`, sonra Vercel dağıtımının `Ready` olmasını
   bekleyin.
5. Siteyi `Ctrl + F5` ile yenileyin ve ilk sahip kaydını yalnızca bir kez yapın.

Parolanızı, yönetici erişim kodunuzu veya borsa anahtarınızı GitHub'a yüklemeyin.
