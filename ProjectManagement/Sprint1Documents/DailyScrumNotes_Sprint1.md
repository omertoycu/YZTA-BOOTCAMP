# Sprint 1 — Daily Scrum Notları

> Format: Her gün, her üye 3 soruyu asenkron olarak Slack kanalında yanıtlar.
> 1) Dün ne yaptım? 2) Bugün ne yapacağım? 3) Önümde engel var mı?

---

## 2026-07-02 — Pivot Günü

**Ömer Faruk Toycu**
1. Dün: EvRadar konsepti için piyasa/rakip analizi yapıldı; sonuç olarak konumun (kiracı odaklı arama asistanı) rekabetçi bir farklılaşma sunmadığı görüldü.
2. Bugün: Ürün konsepti PortföyAI'a (emlak danışmanı için AI kapanış asistanı) pivot edildi. README, teknik yol haritası ve backend iskeleti bu doğrultuda yeniden kuruldu.
3. Engel: Sprint 1'in bitimine 3 gün kalmışken pivot yapılması, kapsamın auth + multi-tenant RLS + temel CRUD + Matching Agent MVP ile sınırlı tutulmasını gerektiriyor. iyzico sandbox aktivasyonu ve WhatsApp Business başvurusu manuel onay süreçleri olduğu için bugün başlatıldı.

---

## 2026-07-02 — Docker'da Uçtan Uca Test ve RLS Düzeltmeleri

**Ömer Faruk Toycu**
1. Dün: Pivot sonrası README, teknik yol haritası ve backend iskeleti (auth, RLS migration, Matching Agent) yazıldı ama hiç çalıştırılmadı.
2. Bugün: `docker-compose up` ile backend gerçek bir Postgres'e karşı çalıştırıldı. Üç kritik RLS açığı bulundu ve düzeltildi: (1) Postgres superuser'ları RLS'yi atlıyor, (2) `SET LOCAL` commit sonrası sıfırlanıyor ve boş string cast hatası veriyordu, (3) login'in cross-tenant e-posta araması RLS ile çelişiyordu. Ayrıca eksik `GET /offices/me` endpoint'i, tutarlı hata yönetimi ve 12 testlik bir test suite'i eklendi. CI şimdi yeşil.
3. Engel yok — Sprint 1'in kalan kapsamı (iyzico sandbox talebi, WhatsApp başvurusu) manuel/kurumsal işlemler olduğu için ekibin (tek kişilik) kendisi tarafından başlatılması gerekiyor; bunlar Sprint 2'ye devredildi.

---

*(Sonraki günler eklenecektir.)*
