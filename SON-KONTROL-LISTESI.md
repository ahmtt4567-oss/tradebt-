# ProTreBot V27 — Son Kontrol Listesi

## Yazılım doğrulaması

- [x] V26 Testnet-First emir, Stop/TP, akış ve otonom tarama motoru korundu.
- [x] Bulut Operasyon ve Kanıt Merkezi eklendi.
- [x] Testnet kararları, planları ve olayları PostgreSQL'de kalıcılaştırıldı.
- [x] Sunucu yeniden başlatıldığında Testnet otomasyonu ve emir kilidi kapalı başlıyor.
- [x] API/Secret ve yönetici kodları kanıt veritabanına yazılmıyor.
- [x] Gerçek para kanalı varsayılan olarak kilitli.
- [x] Ön yüz üretim derlemesi ve arka uç testleri tamamlandı.
- [x] `.env`, çalışma verisi, `node_modules`, `dist` ve `.venv` ZIP dışında tutuldu.

## Yayın doğrulaması

- [ ] GitHub kökünde `backend`, `frontend`, `database`, `render.yaml` görünüyor.
- [ ] Render `/api/health` yanıtı `version: 27.0.0` gösteriyor.
- [ ] Render yanıtı `cloud_evidence: KALICI` gösteriyor.
- [ ] Vercel'de **OPERASYON & KANIT** sekmesi açılıyor.
- [ ] Demo bağlantı testi başarılı.
- [ ] Otonom taramada Son Karar açıklaması düzenli güncelleniyor.
- [ ] Açılan Testnet pozisyonu ve Stop/TP sayıları operasyon ekranında görünüyor.
- [ ] Sunucu yeniden dağıtıldıktan sonra kanıt olay sayısı korunuyor.

## Ürün olarak satmadan önce kalanlar

- [ ] Çok kullanıcılı hesap ve veri izolasyonu.
- [ ] Kullanıcı başına şifreli borsa anahtarı kasası.
- [ ] E-posta doğrulama, parola sıfırlama ve oturum yönetimi.
- [ ] Abonelik, ödeme, fatura ve lisans iptal akışı.
- [ ] Merkezi hata izleme, yedekleme ve geri yükleme tatbikatı.
- [ ] En az 30 aktif gün ve 100 kapanmış Testnet işlem kanıtı.
- [ ] Gerçek para özelliğinden önce bağımsız güvenlik ve hukuki inceleme.

Testnet sonucu gelecekteki getiriyi garanti etmez. Gerçek para kapıları tamamlanana kadar canlı
API anahtarlarını eklemeyin.
