# V26 geçiş planı

## Şimdi açık olan kanal: Binance Futures Demo/Testnet

Testnet, Binance'in emir, bakiye ve pozisyon akışını sanal varlıkla çalıştırır. Bu sayede
pozisyon, kaldıraç, LIMIT/MARKET, Stop, TP ve borsa hata cevaplarını gerçek parayı riske
atmadan görebiliriz. Paper simülasyonu bu sürümde kapalıdır.

Demo anahtarlarını yalnızca Render servisinde tanımlayın:

```text
BINANCE_DEMO_API_KEY
BINANCE_DEMO_SECRET_KEY
```

## Hazır fakat kilitli kanal: Gerçek Binance USD-M Futures

Canlı ekran ve altyapı görünürdür. Aşağıdaki iki secret boşken bağlantı ve emir düğmeleri
fail-closed kalır:

```text
BINANCE_LIVE_API_KEY
BINANCE_LIVE_SECRET_KEY
```

Bu değerleri Vercel'e, GitHub'a, ekran görüntüsüne veya sohbet mesajına koymayın.

## Canlıya geçiş kapıları

1. Testnet'te en az 30 aktif gün ve 100 kapanmış işlem.
2. Stop/TP, kısmi kapama, ağ kesintisi ve acil durdurma tatbikatları.
3. Maksimum düşüş, ücret ve kayma raporunun kabul edilmesi.
4. Yalnızca Futures işlem izni bulunan yeni canlı API anahtarı.
5. Para çekme ve transfer izinlerinin kapalı olması.
6. Mümkünse sabit çıkış IP'si ve Binance IP kısıtlaması. Dinamik IP kullanan ücretsiz
   sunucuda canlı kanal açılmamalıdır.
7. Salt-okunur bağlantı testi ve ONE-WAY pozisyon modu doğrulaması.
8. Risk politikasının yazılı onayı.
9. Sunucuda 24 saatlik risk izni.
10. Her emir oturumu için 5 dakikalık son kilit.

Uygulama/sunucu yeniden başlatıldığında 24 saatlik izin ve son kilit otomatik iptal olur.

## Eski anahtar uyarısı

Önceki ekran görüntülerinde görünen bütün Demo veya canlı anahtarları Binance'ten silip yeniden
oluşturun. Görüntüye girmiş bir Secret artık güvenli kabul edilmez.
