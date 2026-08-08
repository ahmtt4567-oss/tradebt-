# V25.1 Otonom Paper Avcısı

## Neden bu sürüm var?

Önceki Paper Autopilot, 10.000 USDT sanal bakiye gösterse de otomatik pozisyonları 50–125 USDT ile sınırlıyordu. Doğru yönlü %1'lik bir harekette bile brüt sonuç 0,50–1,25 USDT civarında kaldığı için performans ekranda anlamlı görünmüyordu.

V25.1 sabit tutarı kaldırır. Bot, uygun adayı kendi seçer ve sanal pozisyonu Stop riski ile portföy tavanından hesaplar.

## Otonom akış

1. En likit USDT pariteleri taranır.
2. LONG/SHORT adayları güven, hacim oranı, fiyat değişimi, kırılım ve tuzak riskine göre puanlanır.
3. Piyasa Kalkanı, rejim, likidite, korelasyon, kalite, seans, çoklu zaman, mum kapanışı ve fiyat tazeliği kapıları korunur.
4. Giriş–Stop mesafesinden risk bütçesi hesaplanır.
5. Kullanılabilir sanal bakiye, mevcut maruziyet ve profil tavanı uygulanır.
6. TP1/TP2/TP3 kısmi kapanış planının ücret sonrası net senaryosu profil eşiğinin altındaysa işlem açılmaz.
7. Uygunsa yalnızca yerel Paper cüzdanda pozisyon açılır ve bütün gerekçeler Olay Akışına yazılır.

## Profiller

| Profil | Coin evreni | Tek işlem tavanı | Toplam maruziyet | Stop risk bütçesi | Plan net eşiği |
|---|---:|---:|---:|---:|---:|
| Temkinli | 18 | Bakiye %8 | Bakiye %24 | Bakiye %0,18 | 2,50 USDT |
| Dengeli | 24 | Bakiye %15 | Bakiye %45 | Bakiye %0,30 | 5,00 USDT |
| Hızlı | 30 | Bakiye %18 | Bakiye %54 | Bakiye %0,40 | 5,00 USDT |

Her durumda tek Paper pozisyon en fazla 2.000 USDT, eşzamanlı pozisyon sayısı en fazla 3'tür. Günlük 250 USDT sanal zarar kilidi, iki ardışık kayıp soğuması ve acil fren korunur.

## Nasıl kullanılır?

1. Eski kopyayı `DURDUR.bat` ile kapatın.
2. V25.1 ZIP'ini OneDrive dışında yeni bir klasöre tamamen çıkarın.
3. İlk kez `KURULUM.bat`, sonraki açılışlarda `BASLAT.bat` çalıştırın.
4. Panelden **V25 Komuta → Paper Autopilot** sekmesine girin.
5. Önce **Dengeli** profil ile **Otonom Avcıyı Başlat** düğmesine basın.
6. Coin Avcısı kısa listesini, son sermaye hesabını, Stop senaryosunu ve Olay Akışını izleyin.
7. En az 30 aktif gün ve 100 kapanmış Paper işlemden önce profili sonuçlara göre yargılamayın; tek gün istatistiksel kanıt değildir.

## Sonuçları nasıl okumak gerekir?

- **Plan net senaryosu**, fiyatın TP1, TP2 ve TP3'e sırasıyla ulaştığı varsayımıdır; tahmin değildir.
- **Stop senaryosu**, Stop seviyesine ulaşılması hâlindeki yaklaşık sanal zarar ve Paper ücretidir.
- **5 USDT referansı**, kullanıcının gözlem kolaylığı içindir. Her gün 5 USDT üretmek zorunlu veya garanti değildir.
- Gerçek performans; net PnL, en az 100 kapanmış işlem, kazanma oranı, Profit Factor ve maksimum düşüş birlikte incelenerek değerlendirilmelidir.

## Güvenlik

V25.1 Otonom Paper motoru para yatırmaz, çekmez, transfer etmez ve borsaya emir göndermez. Canlı piyasa verisini yalnızca analiz için okur. V25 Live Guard ayrı bir modüldür; bu güncelleme onun emir izinlerini veya tavanlarını değiştirmez.

Geçmiş veya Demo performansı gelecekte kâr garantisi değildir.
