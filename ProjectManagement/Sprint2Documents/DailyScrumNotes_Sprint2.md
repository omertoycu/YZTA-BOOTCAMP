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

*(Sonraki günler eklenecektir.)*
