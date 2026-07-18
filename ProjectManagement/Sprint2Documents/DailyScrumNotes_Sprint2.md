# Sprint 2 — Daily Scrum Notları

> Format: Her gün, her üye 3 soruyu asenkron olarak Slack kanalında yanıtlar.
> 1) Dün ne yaptım? 2) Bugün ne yapacağım? 3) Önümde engel var mı?

---

## 2026-07-02 — Erken Başlangıç (resmi sprint tarihinden önce)

**Ömer Faruk Toycu**
1. Dün: Sprint 1 kapanış işleri (GET /offices/me, hata yönetimi, test kapsamı) tamamlandı, CI yeşil.
2. Bugün: Resmi Sprint 2 başlangıcı (6 Temmuz) beklenmeden Pricing Agent (ChromaDB k-NN emsal fiyat aralığı) ve Scoring Agent (kural bazlı yanıt hızı + mesaj sayısı + bütçe tutarlılığı skoru) yazıldı. `lead_scores` tablosu ve `leads.message_count`/`last_contacted_at` kolonları eklendi. Docker'da uçtan uca doğrulandı, 22/22 test yeşil.
3. Engel yok. Not: Pricing Agent şu an her ofisin emsallerini sadece kendi portföyüyle sınırlıyor (Postgres RLS ile tutarlı); pazar-geneli (cross-tenant) emsal verisi ileride ayrı, dar yetkili bir rolle değerlendirilebilir.

---

## 2026-07-02 (devam) — Next.js Ofis Paneli

**Ömer Faruk Toycu**
1. Dün/bugün erken saatler: Pricing/Scoring Agent tamamlandı.
2. Bugün: Sprint 2'nin 10. story'si — Next.js 16 (App Router) + TypeScript + Tailwind ile ofis paneli iskeleti kuruldu: giriş/kayıt, portföy listesi + fiyat önerisi, lead listesi + skorlama/eşleştirme tetikleme ekranları. `GET /leads` ve `GET /leads/{id}` endpoint'leri eksikti, eklendi. Backend'e CORS middleware eklendi (frontend farklı origin'den istek atıyor). `next build` başarılı, backend'e gerçek isteklerle (CORS header'ları dahil) uçtan uca doğrulandı.
3. Engel yok. Not: `next lint` Next.js 16'da flat ESLint config (`eslint.config.js`) gerektiriyor, henüz eklenmedi — `next build`'in TypeScript kontrolü şimdilik yeterli güvence sağlıyor, flat config Sprint 2 içinde eklenmeli.

---

## 2026-07-03 — WhatsApp Intake Agent, İlan İçe Aktarma, Konum Bazlı Eşleştirme, Fotoğraf Yükleme, Tasarım Sistemi

**Ömer Faruk Toycu**
1. Dün: Ofis paneli iskeleti (giriş, portföy/lead listeleri) kuruldu.
2. Bugün: Story 7'nin (WhatsApp Intake Agent) webhook kod tarafı tamamlandı — Meta Cloud API şemasına göre `POST/GET /webhooks/whatsapp`, `X-Hub-Signature-256` HMAC doğrulaması, `whatsapp_inbound_events` tablosuyla idempotency. Ardından backlog'da olmayan üç ek özellik eklendi: (1) Sahibinden sayfa kaynağı yapıştır → form doldur (`extract-from-html`, JSON-LD + CSS seçiciler), (2) konum/yarıçap bazlı eşleştirme (Nominatim geocoding + DB önbellek, `matching.py` güncellendi), (3) S3-uyumlu ilan fotoğrafı yükleme. Son olarak ofis paneli, verilen mockup'a göre tamamen yeni bir tasarım sistemine (bento-grid dashboard, sol sidebar, 6 adımlı rehberli ilan ekleme sihirbazı) geçirildi. Backend + PostgreSQL Railway'e, ofis paneli Vercel'e deploy edildi; migration'lardaki bootstrap rol şifreleri rotate edildi.
3. Engel: WhatsApp Intake Agent, Meta Business Manager doğrulaması tamamlanana kadar canlı numarayla test edilemiyor (manuel/kurumsal işlem). Sahibinden seçicileri gerçek HTML görülmeden yazıldı, gerçek yapıştırılmış kaynaklarla doğrulanması gerekiyor. Railway Bucket (S3) kurulumu credential girme aşamasında, ilk gerçek fotoğraf yüklemesiyle public-read erişimi doğrulanacak.

---

## 2026-07-06 / 07-07 — Bakım Maratonu (canlı kullanım geri bildirimleri)

**Ömer Faruk Toycu**
1. Dün: Ürün canlıda gerçek ofis verisiyle (kendi portföyümüz) kullanılmaya başlandı; ilk gerçek kullanım geri bildirimleri toplandı.
2. Bugün: Geri bildirimlerden gelen büyük bakım paketi tamamlandı — (1) Eşleştirme: Nominatim rate-limit düzeltmesi, mahalle adının ilan başlığından yakalanması (Sahibinden ilçe alanı sadece il/ilçe taşıyor, "Çekirge" gibi mahalleler başlıkta), bütçede ±%5 tolerans bandı + eşleşme gerekçesi notları. (2) Satılık/kiralık ayrımı: Pricing Agent kiralık emsalleri satılıklarla karıştırıp anlamsız aralık üretiyordu, `listing_type` alanı eklendi ve emsaller buna göre filtreleniyor. (3) ChromaDB endeksi her deploy'da sıfırlanıyordu — sorgudan önce ofis başına bir kez çalışan otomatik yeniden indeksleme (self-heal) eklendi. (4) Sahibinden toplu aktarım (`/listings/import`): kaynak yapıştır → inceleme kartları → onaylananlar kapak fotoğrafıyla içeri; gerçek mağaza verisiyle uçtan uca doğrulandı. (5) Adaylar sayfası 4 sekmeli yeniden tasarlandı; şifre politikası, profil sayfası + ofis logosu, bildirim zili eklendi.
3. Engel: WhatsApp kalıcı erişim token'ı alınamıyor (Meta code-190 hatası) — System User üzerinden yeniden denenecek. Webhook doğrulaması geçmiş durumda, tek tıkanma bu.

---

## 2026-07-08 — Otomatik Yanıt Botu + Ürün Sadeleştirme

**Ömer Faruk Toycu**
1. Dün: Bakım maratonu kapandı, tüm değişiklikler canlıya alındı.
2. Bugün: (1) WhatsApp otomatik yanıt botu yazıldı — MENÜ/İLANLAR/DURUM/DANIŞMAN komutları tamamen deterministik yanıtlanıyor (LLM maliyeti sıfır), arama kriterleri dolduğunda gerçek eşleşmeler otomatik gönderiliyor, alakasız mesajlara sessiz kalınıyor. Canlı kullanım gözlemiyle kritik bir eksik bulundu ve düzeltildi: ilk mesajında kriterlerini yazan yeni aday karşılama+kısayol mesajını hiç görmüyordu — artık her yeni aday önce karşılamayı alıyor. (2) Aday adı WhatsApp profilinden yakalanıyor, panel telefon yerine isim gösteriyor; danışmana yeni aday anlık bildirimi eklendi. (3) Dashboard "Bugün" aksiyon merkezi olarak yeniden tasarlandı. (4) **Scoring Agent üründen kaldırıldı** — teknik olarak çalışıyordu ama gerçek kullanımda karar değiştirmiyordu; tablo, endpoint ve rapor alanlarıyla birlikte silindi.
3. Engel yok. Not: WhatsApp profil fotoğrafı hiçbir koşulda alınamıyor — Meta webhook'u sadece profil adını taşıyor (platform kısıtı), isim yeterli görüldü.

---

## 2026-07-09 — Yapılandırılmış Konum + Mobil

**Ömer Faruk Toycu**
1. Dün: Bot + dashboard yeniden tasarımı canlıya alındı.
2. Bugün: (1) Yapılandırılmış konum altyapısı: repo içine gömülü Türkiye sözlüğü (81 il / 973 ilçe / 32 bin mahalle, harici API yok), ilan formunda şehir→ilçe→mahalle sıralı autocomplete, ilçeden şehir çıkarımı (portal aktarımı ve sesli not da otomatik şehir etiketi kazanıyor). (2) Tek-ilan sihirbazındaki "kaynak yapıştır" adımı kaldırıldı — danışman bu işi hep toplu yapıyor, toplu aktarım tek yol olarak bırakıldı. (3) Fiyat önerisi arayüzü tek karta indirildi, teknik model adları kullanıcı arayüzünden temizlendi. (4) Mobil/responsive düzeltmeleri (gerçek kullanıcı şikâyeti): landing hero mobilde hiç çalışmıyordu — mobile özel varyant eklendi; panel yüksekliği mobil adres çubuğuyla kayıyordu — düzeltildi. Mobil görünüm 390×844 viewport'ta otomasyonla doğrulandı.
3. Engel yok.

---

## 2026-07-10 — Ulaşım Raporu Kararı

**Ömer Faruk Toycu**
1. Dün: Konum altyapısı + mobil düzeltmeler canlıya alındı.
2. Bugün: Ulaşım/Konum Raporu'nun "boş değer gösteriyor" şikâyetinin kök nedeni teşhis edildi: Google Directions API `REQUEST_DENIED` dönüyor (key'de Directions etkin değil/kısıtlı). Düzeltme (gerçek hata nedenini gösterme + rapor zenginleştirme) kodlanıp doğrulandı; buna rağmen özelliğin harici API bağımlılığı ve PDF üretim zinciri karmaşıklığına değmediğine karar verildi — **özellik üründen tamamen kaldırıldı**, bağımlılıkları (WeasyPrint, Maps key) da temizlendi.
3. Engel: iyzico aktivasyon maili hâlâ yanıtsız; Google AI Studio kredisi tükendi, sesli özellikler prod'da 429 dönüyor (bakiye eklenecek).

---

## 2026-07-19 — Sprint Kapanışı

**Ömer Faruk Toycu**
1. Dün: Son düzeltmeler ve dokümantasyon çalışması.
2. Bugün: Sprint kapanışı — 308 backend testi + ruff izole Docker+Postgres ortamında yeşil, CI yeşil, canlı ortamlar sağlıklı. Sprint Review ve Retrospective yazıldı (bkz. README). Sprint 3 backlog'u iki eksende netleştirildi: canlıya alma (WhatsApp uçtan uca + iyzico) ve danışman verimliliği (ilan vitrini, randevu/takvim, durgun portföy uyarısı, AI maliyet optimizasyonu, kendi mağazasından Apify ile aktarım) — toplam 44 puan.
3. Engel: Üç dış bağımlılık Sprint 3'e devrediyor — iyzico sandbox maili, Meta kalıcı token (System User), AI Studio kredisi. Sprint 3'ün ilk günü üçü için de takip aksiyonu alınacak.
