# V27 — Bulut Operasyon ve Kanıt Merkezi

## Bu sürüm neyi çözüyor?

V26 Testnet motoru emir ve pozisyonları Binance Demo hesabında çalıştırıyordu; ancak bulut
sunucusunun geçici dosya alanı yeniden başlatmada yerel karar kayıtlarını kaybedebilirdi.
V27, anahtar içermeyen Testnet çalışma durumunu PostgreSQL'e kaydeder ve yeni bir operasyon
ekranında görünür kılar.

## Yeni özellikler

- Son otonom tarama zamanı, tur sayısı ve **neden işlem açılmadı** açıklaması.
- Binance Demo bakiyesi, açık PnL, pozisyon, normal emir ve Stop/TP koruma sayısı.
- Açık pozisyonlarda giriş, mark fiyatı, miktar, kaldıraç, marjin türü ve likidasyon seviyesi.
- 30 aktif gün / 100 kapanış / tatbikatlardan oluşan Testnet kanıt sertifikası.
- PostgreSQL'de kalıcı karar ve işlem olay defteri.
- Sunucu katmanı ücretsiz olduğunda 7/24 taramanın kesilebileceğini gösteren açık uyarı.
- Manuel **Kanıtı Şimdi Kaydet** düğmesi.

## Kaydedilmeyen bilgiler

- Binance API Key ve Secret Key
- Yönetici erişim kodu
- Parola veya müşteri kimlik bilgisi
- Gerçek para gönderme izni

## Güvenlik davranışı

- V27 operasyon uçları emir oluşturamaz.
- Testnet otomasyonu sunucu yeniden başlatıldıktan sonra kendiliğinden açılmaz.
- Demo emir kilidi her yeniden başlatmada kapanır.
- Gerçek para kanalı önceki 10 güvenlik kapısı tamamlanmadan kilitli kalır.
- Testnet sonucu ve geçmiş kayıtlar gelecekte kâr garantisi vermez.

## Çalışma koşulu

Ücretsiz Render servisi boşta uyuyabildiği için kesintisiz tarama sağlamaz. İlk yayın ve ekran
kontrolü ücretsiz katmanda yapılabilir. 7/24 Testnet kanıt toplama aşamasında sürekli çalışan
bir sunucu planı gerekir.
