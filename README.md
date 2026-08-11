# ProTreBot Elite X V26 — Testnet-First / Live-Ready

Bu sürümde **Paper kapalıdır**. Ana çalışma motoru Binance USD-M Futures Demo/Testnet'tir.
Gerçek Futures ekranı ve altyapısı hazırdır; ancak canlı API anahtarları, salt-okunur bağlantı,
Demo sertifikası, risk politikası, 24 saatlik izin ve 5 dakikalık son kilit tamamlanmadan
gerçek emir gönderemez.

> Testnet sonucu gerçek piyasa sonucunu ve kârı garanti etmez. İlk kurulumda canlı anahtarları
> boş bırakın; yalnızca Demo anahtarlarını bağlayın.

## Güvenlik modeli

- API ve Secret anahtarları tarayıcıya, GitHub'a veya Vercel'e yazılmaz.
- Anahtarlar yalnızca Render **Environment** bölümünde tutulur.
- Uygulama yeniden başlatılınca canlı işlem izni ve kısa süreli emir kilidi iptal olur.
- Para çekme ve transfer izni bu proje için kullanılmaz.
- Canlı emir kanalı, eksik olan tek bir güvenlik kapısında bile kapalı kalır.

## 1. GitHub'a yükleme

Paketin içindeki dosyaları özel `ProTreBot-Web` deponuzun köküne yükleyin. Şunları yüklemeyin:

- `.env` ve API anahtarları
- `node_modules`, `dist`, `.venv`
- `backend/data`, günlükler veya çalışma zamanı kayıtları

## 2. Render — arka uç

Render mevcut depodaki `render.yaml` dosyasını kullanır. Serviste şu değerler bulunmalıdır:

| Değişken | İlk kurulum değeri |
|---|---|
| `PROTREBOT_WEB_ACCESS_TOKEN` | En az 24 karakterlik yönetici kodunuz |
| `PROTREBOT_CORS_ORIGINS` | Tam Vercel adresiniz |
| `BINANCE_DEMO_API_KEY` | Binance Futures Demo API Key |
| `BINANCE_DEMO_SECRET_KEY` | Binance Futures Demo Secret Key |
| `BINANCE_LIVE_API_KEY` | Şimdilik boş |
| `BINANCE_LIVE_SECRET_KEY` | Şimdilik boş |

Değişiklikten sonra **Manual Deploy > Deploy latest commit** çalıştırın. Sağlık kontrolü:

`https://protrebot-api.onrender.com/api/health`

Ücretsiz Render servisi boşta uyur ve ilk istekte gecikebilir. 7/24 Testnet takibi ve ileride
canlı işlem için sürekli çalışan ücretli servis gerekir.

## 3. Vercel — ön yüz

Vercel projesinde Root Directory `frontend` olmalıdır. Ortam değişkenleri:

| Değişken | Değer |
|---|---|
| `VITE_API_URL` | `https://protrebot-api.onrender.com` |
| `VITE_WEB_ACCESS_REQUIRED` | `true` |

Ana sayfada yönetici erişim kodunu girin. Bu kod Binance anahtarı değildir.

## 4. Testnet doğrulama sırası

1. `Yayın Kapıları` sekmesinde Demo kanalının bağlı olduğunu doğrulayın.
2. `Testnet Komuta` bölümünde bakiye ve pozisyon modunu kontrol edin.
3. Önce emir testi, sonra küçük Demo MARKET/LIMIT emri deneyin.
4. Stop ve TP emirlerinin Binance Demo hesabında göründüğünü doğrulayın.
5. Acil durdurma tatbikatı yapın ve tüm Demo emirlerinin kapandığını denetleyin.
6. En az 30 aktif gün ve 100 kapanmış Demo işlem ile sonuç toplayın.

Canlı kanalın ayrıntılı kapıları için [V26-TESTNET-FIRST.md](V26-TESTNET-FIRST.md) dosyasına bakın.
