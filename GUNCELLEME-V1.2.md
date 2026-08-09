# ProTreBot Web V1.2 — Boş Ekran ve Render Koruması

Bu bakım güncellemesi, **50 USDT Demo Aç** işleminden veya geçici Render/Binance
veri hatasından sonra panelin beyaz ekrana düşmesini engeller.

## Düzeltilenler

- `/paper/account` hata cevabı artık Paper hesabı sanılarak ekrana basılmaz.
- Son sağlam Paper hesap görünümü, geçici API hatasında korunur.
- Eksik/eski pozisyon alanları güvenli varsayılanlarla tamamlanır.
- Beklenmeyen bir arayüz hatasında beyaz sayfa yerine **Güvenli Ekran
  Koruması** ve yenileme düğmesi gösterilir.
- Rejim kararlılığı veri sağlayıcısı geçici olarak yanıt vermediğinde güvenli
  `BEKLE` durumu döner.
- V11 laboratuvarında yetersiz canlı mum verisi kontrolsüz 500 üretmez;
  otomatik Paper girişleri kapalı tutularak yeniden deneme beklenir.
- Paper hesap uç noktası canlı fiyat yenilemesi aksasa bile son kaydı okumaya
  devam eder.

## Tek seferlik güncelleme

1. ZIP'i bilgisayarınızda çıkarın.
2. İçindeki `backend` ve `frontend` klasörlerini GitHub deponuzun köküne
   sürükleyin. GitHub mevcut klasörlerle birleştirir.
3. Altta **Commit changes** düğmesine basın.
4. Render servisinde yeni dağıtımın `Live`, Vercel'de dağıtımın `Ready`
   olmasını bekleyin.
5. Siteyi `Ctrl + F5` ile yenileyin.

Bu sürüm yalnızca Paper/demo işlem kullanır. Gerçek ve Testnet emir kanalları
kapalı kalır; gerçek para veya borsa anahtarı bu pakete konmaz.
