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

*(Sonraki günler eklenecektir.)*
