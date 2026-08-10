# V20.3.1 — Binance Futures Demo Köprüsü

Bu sürüm yalnızca Binance USD-M Futures **Demo Trading** hesabına bağlanır. Gerçek Binance emir sunucusu bağlayıcıda bulunmaz.

## İlk bağlantı

1. Binance Demo API Yönetimi ekranında oluşturduğunuz **Demo API Key** ve **Demo Secret Key** hazır olsun.
2. `BINANCE-DEMO-AYARLA.bat` dosyasına çift tıklayın.
3. Yerel penceredeki iki alana anahtarları yapıştırın. Yazıların görünmemesi normaldir.
4. ProTreBot açıksa `DURDUR.bat`, ardından `BASLAT.bat` çalıştırın.
5. Panelde **V20 Komuta → Binance Demo** sekmesine girip **Bağlantıyı Test Et** düğmesine basın.

Anahtarlar `backend/.env` içinde yalnızca yerel bilgisayarda tutulur. Bu dosya ZIP paketine ve Git kaydına alınmaz. Anahtarları sohbete, e-postaya veya ekran görüntüsüne koymayın.

## Güvenlik kilitleri

- Sabit sunucu: `https://demo-fapi.binance.com`
- Gerçek Binance emir adresi yoktur.
- Uygulama her açılışta emir kilitli başlar.
- Emir vermek için `DEMO` yazarak 10 dakikalık kilidi elle açmak gerekir.
- En fazla 100 sanal USDT marjin, 2x kaldıraç ve 200 USDT Demo pozisyon büyüklüğü.
- En fazla 3 açık Demo pozisyonu.
- Hesap **Tek Yön / One-way** pozisyon modunda olmalıdır.
- Stop emri kurulamazsa bot giriş emrini iptal eder ve dolmuş Demo pozisyonu güvenlik için kapatmaya çalışır.
- Belirsiz sunucu yanıtında emir körlemesine tekrar gönderilmez; açık emirlerden doğrulanır.

## BTC minimum miktar notu

BTC gibi pahalı pariteler borsanın minimum kontrat miktarı nedeniyle düşük marjinle açılamayabilir. V20.3.1 yalnızca sanal Demo hesapta 100 USDT marjine kadar izin verir. Panel gereken minimumu yine sağlayamazsa nedenini açıkça gösterir; gerçek emir kanalı hiçbir durumda açılmaz.

## Stop ve hedefler

Piyasa emri dolunca Stop önce kurulur. Miktar borsa minimumuna uygunsa TP1 ve TP2 yüzde 30'ar reduce-only, TP3 kalan pozisyonu kapatan koşullu emir olarak eklenir. Çok küçük miktarda TP1/TP2 borsa minimumuna takılırsa Stop aktif kalır ve bu iki hedef panelde izleme hedefi olarak gösterilir.

Bu yazılım eğitim ve test içindir; Demo sonuçları gerçek piyasa performansını garanti etmez.
