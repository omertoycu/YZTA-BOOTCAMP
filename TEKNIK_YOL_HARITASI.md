# PortföyAI — Detaylı Teknik Yol Haritası

> Bu doküman [Girişim Analizi Raporu](./PortfoyAI_Girisim_Analizi_ve_Teknik_Rapor.md)'nda çizilen stratejiyi uygulanabilir, story bazlı mühendislik planına döker. README'deki sprint tabloları "ne" yapılacağını, bu doküman "nasıl" yapılacağını anlatır.

---

## 1. Mimari Genel Bakış

```
portfoyai/
├── backend/                     # FastAPI + LangGraph + PostgreSQL
│   ├── app/
│   │   ├── main.py               # FastAPI app entrypoint
│   │   ├── core/
│   │   │   ├── config.py         # Pydantic Settings (env vars)
│   │   │   ├── security.py       # JWT encode/decode, password hashing
│   │   │   └── db.py             # SQLAlchemy engine/session, RLS session var
│   │   ├── middleware/
│   │   │   └── tenant.py         # her request'te SET app.current_office_id
│   │   ├── models/                # SQLAlchemy ORM modelleri
│   │   ├── schemas/                # Pydantic request/response şemaları
│   │   ├── api/routes/             # auth, offices, listings, leads, matches, reports
│   │   └── agents/                 # LangGraph node'ları (intake, matching, scoring, pricing, voice)
│   ├── alembic/                    # DB migration'ları (RLS policy'leri dahil)
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                    # Next.js 16 (App Router) + TypeScript + Tailwind — ofis paneli
│   ├── app/
│   │   ├── login/page.tsx        # Ofis kaydı + giriş (tek sayfa, tab ile)
│   │   ├── listings/page.tsx     # Portföy listesi/ekleme + Pricing Agent önerisi
│   │   └── leads/page.tsx        # Lead listesi/ekleme + Scoring/Matching Agent tetikleme
│   ├── lib/api.ts                 # fetch wrapper, JWT localStorage yönetimi
│   └── components/NavBar.tsx
├── .github/workflows/ci.yml     # Lint + test + Railway deploy
├── docker-compose.yml            # Yerel: postgres + backend
└── .env.example
```

**Neden bu ayrım:** Multi-tenant RLS'in doğru çalışması backend'in her request'te `office_id`'yi DB session'a set etmesine bağlı — bu en sık atlanan adım olduğu için `middleware/tenant.py` ayrı ve test edilebilir bir modül olarak izole edildi.

**Frontend'i yerelde çalıştırma:**
```bash
cd frontend
cp .env.local.example .env.local   # NEXT_PUBLIC_API_URL varsayılanı localhost:8010'u gösterir
npm install
npm run dev                        # http://localhost:3000
```
Backend'in `CORS_ORIGINS` ayarı varsayılan olarak `http://localhost:3000`'i kabul eder (bkz. `app/core/config.py`); farklı bir portta çalıştırıyorsanız `.env`'de güncelleyin.

---

## 2. Veri Modeli (PostgreSQL)

| Tablo | Amaç | Kritik kolonlar |
|---|---|---|
| `offices` | Kiracı (tenant) kök varlığı | `id`, `name`, `subscription_plan`, `created_at` |
| `users` | Ofis sahibi / danışman / görüntüleyici | `id`, `office_id`, `role`, `email`, `hashed_password` |
| `listings` | Portföyler | `id`, `office_id`, `agent_id`, `price`, `room_count`, `district`, `status`, `photos` (JSON) |
| `leads` | WhatsApp/manuel gelen talepler | `id`, `office_id`, `source`, `budget_min/max`, `district`, `contact_phone` |
| `conversations` | Intake Agent mesaj geçmişi | `id`, `lead_id`, `channel`, `raw_messages` (JSON) |
| `lead_scores` | Scoring Agent çıktısı | `id`, `lead_id`, `score`, `score_breakdown` (JSON), `computed_at` |
| `matches` | Lead–Listing eşleşmeleri | `id`, `lead_id`, `listing_id`, `match_reason`, `rank` |
| `voice_notes` | Voice-to-Listing kayıtları | `id`, `office_id`, `audio_url`, `transcript`, `draft_listing_json`, `approved_by`, `approved_at` |
| `location_reports` | Üretilen ulaşım PDF kayıtları | `id`, `listing_id`, `target_address`, `pdf_url`, `generated_at` |
| `subscriptions` | iyzico abonelik durumu | `id`, `office_id`, `iyzico_subscription_ref`, `plan`, `status`, `trial_ends_at` |

**RLS kuralı (her tabloda, `offices` hariç):**
```sql
ALTER TABLE listings ENABLE ROW LEVEL SECURITY;
ALTER TABLE listings FORCE ROW LEVEL SECURITY;
CREATE POLICY office_isolation ON listings
  USING (office_id = NULLIF(current_setting('app.current_office_id', true), '')::uuid);
```
Backend, her request başında `tenant` middleware'inde şunu çalıştırır:
```sql
SET LOCAL app.current_office_id = '<request.user.office_id>';
```

**Sprint 1'de canlıda bulunan 3 kritik RLS tuzağı (bkz. migration 0002-0004):**
1. **Postgres superuser'ları RLS'yi her zaman atlar** — `FORCE ROW LEVEL SECURITY` bile superuser'ı etkilemez, sadece tablo sahibini etkiler. Resmi `postgres` Docker imajının `POSTGRES_USER`'ı varsayılan olarak superuser'dır. Çözüm: uygulama, DDL yetkisi olmayan, superuser OLMAYAN ayrı bir `portfoyai_app` rolüyle bağlanır; migration'lar ise superuser (`portfoyai`) ile çalışır (`MIGRATIONS_DATABASE_URL`).
2. **`SET LOCAL` transaction-scoped'dur** — `db.commit()` sonrası tenant context sıfırlanır. Kullanılmamış bir custom GUC, LOCAL scope bitince `NULL` değil **boş string (`''`)** döner, bu da `''::uuid` cast hatasına yol açar. Çözüm: policy ifadesinde `NULLIF(..., '')` kullanılır.
3. **Login, e-posta ile ofis bilinmeden kullanıcı aramalıdır** — bu doğası gereği cross-tenant bir sorgu olduğundan RLS'e tabi olamaz. Tüm uygulamaya `BYPASSRLS` vermek yerine, sadece `offices`+`users` tablolarına `SELECT`/`INSERT` yetkisi olan dar kapsamlı bir `portfoyai_auth` rolü (`AUTH_DATABASE_URL`) sadece `/auth/register` ve `/auth/login` route'larında kullanılır.

Tenant middleware'i atlanırsa (ya da yanlış rolle bağlanılırsa) RLS ya sessizce **tüm satırları gizler** ya da (superuser bypass durumunda) **tüm kiracıların verisini sızdırır** — bu yüzden `backend/tests/test_rls.py`, iki farklı ofisin birbirinin verisini gerçekten göremediğini uçtan uca (gerçek HTTP istekleriyle) doğrular ve CI'da her PR'da çalışır.

---

## 3. API Sözleşmesi (Sprint 1–2 kapsamı)

| Method | Endpoint | Açıklama |
|---|---|---|
| POST | `/auth/register` | Ofis + ilk sahibi kullanıcı oluşturur |
| POST | `/auth/login` | JWT access token döner |
| GET | `/offices/me` | Giriş yapan kullanıcının ofis bilgisi |
| POST | `/listings` | Yeni portföy ekler |
| GET | `/listings` | Ofisin portföylerini listeler (RLS ile otomatik filtrelenir) |
| GET | `/listings/{id}` | Tek portföy detayı |
| GET | `/listings/{id}/pricing-suggestion` | Pricing Agent: ChromaDB k-NN emsal benzerliğiyle fiyat aralığı önerir *(Sprint 2 — erken tamamlandı)* |
| POST | `/leads` | Yeni lead kaydı (WhatsApp webhook veya manuel) |
| GET | `/leads` | Ofisin lead'lerini listeler |
| GET | `/leads/{id}` | Tek lead detayı |
| POST | `/leads/{id}/match` | Matching Agent'ı tetikler, uygun portföyleri döner |
| POST | `/leads/{id}/score` | Scoring Agent: kural bazlı skor + breakdown hesaplar *(Sprint 2 — erken tamamlandı)* |
| POST | `/webhooks/whatsapp` | Meta WhatsApp Cloud API webhook alıcısı (Sprint 2) |
| POST | `/voice-notes` | Ses dosyası yükler, transkript + taslak ilan döner (Sprint 3) |
| POST | `/listings/{id}/location-report` | Ulaşım raporu PDF üretir (Sprint 3) |

---

## 4. Agent Mimarisi — LangGraph Detayı

**State şeması (paylaşılan):**
```python
class AgentState(TypedDict):
    office_id: str
    lead_id: str | None
    raw_input: str
    parsed_criteria: dict | None   # budget, room_count, district
    candidate_listings: list[dict]
    score: dict | None
    pricing_range: dict | None
```

**Node'lar:**
- `intake_node` — Gemini Flash-Lite ile serbest metni `parsed_criteria`'ya çevirir
- `matching_node` — SQL filtresi (Sprint 1: basit `WHERE`; Sprint 2+: ChromaDB benzerlik) ile `candidate_listings` doldurur
- `scoring_node` — kural bazlı ağırlıklı toplam (yanıt hızı %40, mesaj sayısı %30, bütçe tutarlılığı %30) — Sprint 1'de ML **yok**, yeterli etiketli veri birikmeden ML modeline geçilmeyecek
- `pricing_node` — ChromaDB k-NN + istatistiksel aralık (ortalama ± std sapma), "kesin tahmin" değil "benzer ilan aralığı" olarak döner
- `voice_listing_node` (Sprint 3) — Whisper transkript + Gemini ile yapılandırılmış taslak, `approved=False` ile kaydedilir, danışman onayı olmadan `listings` tablosuna yazılmaz

**Hata yönetimi:** Her node'a `retry(max_attempts=2)` + `timeout=15s` eklenir; LLM çağrısı başarısız olursa Sentry'e event gönderilir ve kullanıcıya "tekrar deneniyor" mesajı döner (README Bölüm 3'te belirtilen prod kritik eksik).

---

## 5. Üçüncü Parti Entegrasyon Kontrol Listesi

| Entegrasyon | Aksiyon | Zamanlama | Not |
|---|---|---|---|
| iyzico sandbox | `entegrasyon@iyzico.com`'a abonelik özelliği aktivasyon maili | Sprint 1, gün 1 | Manuel onay süresi belirsiz — en erken başlatılmalı |
| iyzico canlı ürün/plan | `v2/subscription/products` → `pricingPlans` kurulumu | Sprint 2 | Tek ürün + 3 `pricingPlan` (Starter/Professional/Enterprise) |
| WhatsApp Business doğrulama | Meta Business Manager başvurusu | Sprint 1 sonu | Günler sürebilir; paralel olarak bir BSP (VatanSMS/Invekto) ile geçici başlangıç |
| BSP seçimi | VatanSMS/Invekto fiyat/API karşılaştırması | Sprint 2 başı | Kendi Meta başvurunuz onaylanana kadar köprü çözüm |
| Google Maps Directions API | API key + billing hesabı açma | Sprint 3 başı | Ulaşım raporu için ön koşul |
| Whisper API (OpenAI) | API key alma | Sprint 3 başı | Voice-to-Listing için ön koşul |

---

## 6. Test Stratejisi

- **Birim testleri:** `pytest` ile her agent node'u (mock LLM yanıtıyla) izole test edilir
- **RLS entegrasyon testi:** İki farklı `office_id` ile aynı endpoint'e istek atılıp, bir ofisin diğerinin verisini asla göremediği doğrulanır — bu, multi-tenant SaaS'ta en kritik güvenlik testidir, Sprint 1'de yazılmalı
- **Agent güvenilirlik testi:** Voice-to-Listing ve Pricing Agent çıktıları için "düşük güven" senaryoları (gürültülü ses, az veri) manuel test edilir; rapor bu özelliklerin teknik risk taşıdığını belirtiyor
- **CI:** Her PR'da `pytest` + `ruff`/`flake8` GitHub Actions üzerinde çalışır (bkz. `.github/workflows/ci.yml`)

---

## 7. Altyapı & Deployment

- **Yerel geliştirme:** `docker-compose up` → PostgreSQL + FastAPI (`--reload`)
- **Prod:** Railway (backend + managed PostgreSQL), ortam değişkenleri Railway secret yönetimi ile
- **Secrets:** `GEMINI_API_KEY`, `OPENAI_API_KEY` (Whisper), `GOOGLE_MAPS_API_KEY`, `IYZICO_API_KEY`/`IYZICO_SECRET_KEY`, `WHATSAPP_TOKEN`, `JWT_SECRET`, `DATABASE_URL`, `SENTRY_DSN`
- **Hata izleme:** Sentry SDK, FastAPI middleware olarak entegre; LangGraph node hataları özel tag ile (`agent_name`) gönderilir

---

## 8. Sprint Bazlı Görev Kırılımı

### Sprint 1 — Kalan 3 gün (2–5 Temmuz 2026)
- **Gün 1 (2 Tem):** iyzico aktivasyon maili gönder + WhatsApp Business başvurusunu başlat; backend iskeleti (auth + RLS + Alembic) kurulur
- **Gün 2 (3–4 Tem):** Listing CRUD + Matching Agent MVP (LangGraph tek node, SQL filtre) + RLS entegrasyon testi
- **Gün 3 (5 Tem):** CI/CD (GitHub Actions → Railway) + Sprint Review/Retrospective doldurulur

### Sprint 2 (6–19 Temmuz 2026)
- Hafta 1: iyzico canlı ürün/plan kurulumu, WhatsApp BSP entegrasyonu + Intake Agent webhook
- Hafta 2: Pricing Agent (ChromaDB embedding), Scoring Agent (kural motoru), Next.js ofis paneli iskeleti

### Sprint 3 (20 Temmuz – 2 Ağustos 2026)
- Hafta 1: Voice-to-Listing (Whisper + Gemini + onay akışı), Ulaşım Raporu (Maps + WeasyPrint)
- Hafta 2: Otomatik WhatsApp takip mesajı, production deployment, Sentry, performans/hata yönetimi, demo hazırlığı

---

## 9. Risk Takip Tablosu

| Risk | Etkisi | Azaltma | Durum |
|---|---|---|---|
| Piyasada zaten AI'lı emlak CRM'leri var | Farklılaşma zayıflar | Hero özellikler Voice-to-Listing + Ulaşım Raporu'na kaydırıldı | Uygulanıyor |
| Türkçe sesli AI saha koşullarında güvenilir değil | Kullanıcı güveni kırılabilir | Zorunlu "AI taslak → danışman onayı" akışı | Mimaride zorunlu kılındı |
| Emlakçı portföy verisi eksik/tutarsız | Matching/Scoring yanlış sonuç üretir | Onboarding'de zorunlu alan kontrolü (Sprint 3) | Planlandı |
| WhatsApp Business onay süresi öngörülemez | Sprint 2 gecikebilir | Başvuru Sprint 1 sonunda başlatıldı, BSP ile paralel | Aksiyon alındı |
| iyzico aktivasyonu manuel onaya bağlı | Sprint 1 ödeme story'si bloke olabilir | Talep Sprint 1 gün 1'de gönderiliyor | Aksiyon alındı |
| "Kredi kartsız deneme" pazarlama iddiası teknikle çelişiyor | Güven kaybı | Metin "deneme boyunca ücretsiz, kart doğrulama gerekir" olarak düzeltildi | Uygulandı (README) |

---

## 10. Definition of Done (Story bazlı)

Bir story ancak şu koşullar sağlandığında "tamamlandı" sayılır:
1. İlgili endpoint/agent node için birim testi yazılmış ve geçiyor
2. Multi-tenant etkileyen her değişiklik için RLS testi güncellenmiş
3. `ruff`/`flake8` ve `mypy` (varsa) hatasız
4. CI pipeline'ı yeşil
5. README'deki ilgili Sprint tablosunda checkbox işaretlenmiş ve Sprint Review'e not düşülmüş

---

*Bu doküman, projenin ilerleyişine göre her sprint sonunda güncellenmelidir.*
