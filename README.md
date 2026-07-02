# Takım İsmi
## Takım [151] — PortföyAI

---

# Ürün İle İlgili Bilgiler

## Takım Elemanları

| İsim | Rol |
|------|-----|
| [Ömer Faruk Toycu] | Product Owner |
| [Ömer Faruk Toycu] | Scrum Master |
| [Ömer Faruk Toycu] | Developer |

---

## Ürün İsmi

**PortföyAI** — Emlak Danışmanı için AI Kapanış Asistanı

---

## Ürün Açıklaması

PortföyAI, emlak danışmanının CRM'i değil; ilk WhatsApp mesajından imzaya kadar hiçbir fırsatı kaçırmamasını sağlayan dijital asistanıdır.

Türkiye emlak yazılım pazarında "AI destekli CRM" artık bir farklılaştırıcı değil, sektör standardı (Arveya, RE-OS, EmlakCRMx gibi oyuncular zaten lead skorlama ve AI eşleştirme sunuyor — detaylı rakip analizi için [Girişim Analizi Raporu](./PortfoyAI_Girisim_Analizi_ve_Teknik_Rapor.md)'na bakınız). Bu yüzden PortföyAI, Matching/Scoring/Pricing'i "olması gereken temel özellikler" olarak arkada tutup pazarda gerçekten boş olan iki alana odaklanır: **sesli not ile saniyeler içinde ilan oluşturma** ve **markalı, kapanış aracı olarak kullanılabilecek ulaşım/konum raporu**. Danışman arabada müşteriyle gezerken telefonuna konuşur, PortföyAI ilanı taslak olarak hazırlar; danışman onaylar. Aynı danışman, adayına logolu bir PDF ile "eve 12 dakikada, metroya yürüyerek 4 dakikada" diyen somut bir rapor gönderir. Arka planda WhatsApp'tan gelen her lead otomatik nitelendirilir, skorlanır ve uygun portföylerle eşleştirilir.

---

## Ürün Özellikleri

### Hero Özellikler (Farklılaştırıcı — rakiplerde yok)
- 🎙️ **Sesli Not → İlan Otomasyonu** — Danışman sahada telefonuna konuşur ("3+1, 120 metrekare, asansörlü, otoparklı..."); Whisper ile transkript alınır, LLM ile yapılandırılmış ilan taslağına dönüştürülür. Yayına almadan önce danışman onayı **zorunludur** — AI çıktısı asla otomatik yayınlanmaz.
- 🗺️ **Markalı Ulaşım/Konum Raporu (PDF)** — Google Maps Directions API ile üretilen, ofis logolu, alıcıya doğrudan gönderilebilen kapanış aracı. Piyasada doğrudan muadiline rastlanmayan, en düşük teknik riskli, en yüksek pazarlama değerine sahip özellik.
- 💬 **Otomatik WhatsApp Takip Mesajı** — Lead ilk temastan sonra belirli aralıklarla otomatik nitelikli takip mesajı alır; danışman hiçbir fırsatı unutmaz.

### Temel Özellikler (Table Stakes — sektör standardı, ürün için zorunlu ama pazarlamanın merkezinde değil)
- 🤖 **Intake Agent** — WhatsApp Business API üzerinden gelen mesajları LLM ile ayrıştırır, lead olarak sisteme kaydeder
- 🔗 **Matching Agent** — Bütçe, oda sayısı, bölge kriterlerine göre lead'i uygun portföylerle eşleştirir
- 📊 **Scoring Agent** — Yanıt hızı, mesaj sayısı, bütçe tutarlılığı gibi kural bazlı ağırlıklarla lead'i puanlar (ilk versiyon ML değil, kural motoru)
- 💰 **Pricing Agent** — ChromaDB'de tutulan bölgesel emsal ilan embedding'leri üzerinden k-NN benzerlik ile "benzer ilan fiyat aralığı" önerir (kesin AI fiyat tahmini değil, savunulabilir bir aralık)
- 🏢 **Multi-tenant Ofis Yönetimi** — Ofis sahibi / danışman / görüntüleyici rolleriyle RBAC, PostgreSQL Row-Level Security ile veri izolasyonu
- 💳 **Abonelik ve Faturalama** — iyzico Abonelik Yönetimi ile Starter / Professional / Enterprise planları

---

## Hedef Kitle

- **Birincil hedef:** 1–5 danışmanlı bireysel/mikro emlak ofisleri (büyük zincirler değil — onlar zaten kurumsal CRM'lere bağlı, değişim maliyeti düşük olan küçük ofisler ilk dalga)
- Şu anda WhatsApp ve Excel ile manuel çalışan, dijitalleşmemiş emlak danışmanları
- İl/ilçe bazlı emlakçı WhatsApp gruplarında ve emlak odalarında (TÜGEM, İstanbul Emlak Odası vb.) organik olarak ulaşılabilecek bağımsız acenteler
- Zaman kaybını en çok "sahada not alıp ofise dönünce ilan girme" ve "her lead'i manuel takip etme" adımlarında yaşayan danışmanlar

---

## Kullanılan Teknolojiler

| Katman | Teknoloji | Gerekçe |
|--------|-----------|---------|
| LLM | Google Gemini (Flash-Lite / Flash / Pro karışık) | Yüksek hacimli basit işler Flash-Lite, karmaşık emsal analizi Flash/Pro — maliyet/performans dengesi |
| Ses İşleme | OpenAI Whisper API | Sesli not → transkripsiyon (düşük gürültülü ortam hedefli MVP) |
| Agent Framework | LangChain + LangGraph | Intake / Matching / Scoring / Pricing ajanlarının orkestrasyonu |
| Vektör DB | ChromaDB | Bölgesel emsal ilan embedding'leri (Gemini `text-embedding-004`) |
| Backend | Python 3.11 + FastAPI + SQLAlchemy + Alembic | REST API, migration yönetimi |
| Auth | `python-jose` (JWT) + RBAC | Ofis sahibi / danışman / görüntüleyici rolleri |
| Veritabanı | PostgreSQL (Row-Level Security) | `office_id` bazlı multi-tenant izolasyon |
| Mesajlaşma | WhatsApp Business Cloud API (başlangıçta bir BSP: VatanSMS/Invekto) | Intake Agent kanalı, otomatik takip mesajları |
| Ödeme | iyzico Abonelik Yönetimi (v2 API) | Starter/Professional/Enterprise abonelik planları |
| Harita/Rota | Google Maps Directions API | Ulaşım/konum raporu |
| PDF Üretimi | WeasyPrint | Markalı, logolu ulaşım raporu çıktısı |
| Frontend | Next.js (App Router) + TypeScript + Tailwind CSS | Ofis paneli — lead listesi, portföy yönetimi, rapor önizleme |
| Hata İzleme | Sentry | Prod ortamda LLM/agent hatalarını yakalama |
| CI/CD | GitHub Actions + Railway | Otomatik test + deploy |
| Versiyon Kontrolü | GitHub | Bu repo |

---

## Ajan Mimarisi

```
WhatsApp Mesajı / Sesli Not / Manuel Giriş
              │
              ▼
     ┌─────────────────────┐
     │ LangGraph            │
     │ Orchestrator         │  ← İstek tipini ayırt eder, ilgili ajana yönlendirir
     └──┬──────┬──────┬────┘
        │      │      │
        ▼      ▼      ▼
   [Intake] [Voice-to-  [Matching]
    Agent    Listing]    Agent
        │    Agent          │
        │      │            ▼
        │      │       [Scoring Agent]
        │      │            │
        │      │            ▼
        │      │      [Pricing Agent]
        │      │            │
        └──────┴──────┬─────┘
                       ▼
              ┌─────────────────┐
              │  CRM Katmanı    │  ← Lead/portföy kaydı, skor, eşleşme
              └────────┬────────┘
                       │
                       ▼
        Ofis Paneli (Next.js) + Ulaşım Raporu (PDF)
        + Otomatik WhatsApp Takip Mesajı
```

**Intake Agent:** WhatsApp webhook'undan gelen mesajları LLM ile ayrıştırır, lead olarak kaydeder, ilk otomatik yanıtı gönderir

**Voice-to-Listing Agent:** Whisper ile transkript alır, LLM ile yapılandırılmış ilan taslağı üretir; danışman onayı olmadan yayınlanmaz

**Matching Agent:** Lead kriterlerini (bütçe, oda sayısı, bölge) mevcut portföylerle eşleştirir

**Scoring Agent:** Kural bazlı ağırlıklı skor üretir — yanıt hızı + mesaj sayısı + bütçe tutarlılığı

**Pricing Agent:** ChromaDB'deki emsal ilan embedding'leri üzerinden k-NN benzerlik ile fiyat aralığı önerir

---

## İş Modeli Notu

Starter / Professional / Enterprise üç kademeli abonelik modeli. Starter plana WhatsApp AI erişimi tamamen kapatılmaz — sınırlı sayıda konuşma (örn. ayda 100) dahil edilir ki deneme kullanıcısı ürünün asıl değerini (Intake Agent) görebilsin. 14 günlük deneme, iyzico akışı gereği kart bilgisi doğrulaması ister ancak deneme boyunca ücret alınmaz. Detaylı unit economics ve rakip analizi için [Girişim Analizi Raporu](./PortfoyAI_Girisim_Analizi_ve_Teknik_Rapor.md)'na bakınız.

---

## Teknik Yol Haritası

Detaylı, story bazlı teknik yol haritası ve altyapı kararları için: [📋 TEKNIK_YOL_HARITASI.md](./TEKNIK_YOL_HARITASI.md)

---

## Product Backlog URL

[📋 GitHub Projects — PortföyAI Backlog](https://github.com/omertoycu/YZTA-BOOTCAMP/projects/1)

> *Alternatif: [Miro Backlog Board](#)*

---

# Sprint 1

> 📅 **19 Haziran — 5 Temmuz 2026**
> Sprint puanı hedefi: `31`
>
> ⚠️ **Pivot notu:** Ürün konsepti (EvRadar → PortföyAI) Sprint 1 içerisinde, sprint bitimine 3 gün kala netleşmiştir. Aşağıdaki story seçimi, kalan süreye göre gerçekçi şekilde daraltılmış temel iskelete odaklanır; kapsamlı özellikler Sprint 2/3'e devredilmiştir.

### Backlog Düzeni ve Story Seçimleri

Sprint 1'de hedef, ürünün çalışan ama minimal iskeletini kurmak: multi-tenant auth, temel portföy CRUD'u, ilk Matching Agent taslağı ve ödeme/CI altyapısının başlatılması.

**Sprint 1 User Story'leri:**

| # | User Story | Puan |
|---|-----------|------|
| 1 | Ofis olarak kayıt olabilmeli, JWT ile giriş yapabilmeliyim (FastAPI + `python-jose`) | 8 |
| 2 | Sistem, her tabloda `office_id` bazlı PostgreSQL RLS ile veri izolasyonu sağlamalı | 5 |
| 3 | Danışman olarak portföy (ilan) manuel ekleyip listeleyebilmeliyim | 5 |
| 4 | Matching Agent MVP: bütçe aralığı + oda sayısı + bölge filtresiyle basit eşleştirme (LangGraph tek node) | 8 |
| 5 | iyzico sandbox aktivasyon talebi gönderilmeli ve GitHub Actions CI/CD (Railway deploy) kurulmalı | 5 |

**Sprint Toplam Tahmini Puan: 31**

### Daily Scrum

Daily Scrum Slack kanalı üzerinden asenkron olarak yürütülmektedir (her üye günlük 3 soruyu yanıtlar).

> 📎 [Sprint 1 Daily Scrum Notları](./ProjectManagement/Sprint1Documents/DailyScrumNotes_Sprint1.md)

### Sprint Board Güncellemeleri

> 📸 *Sprint bitiminde ekran görüntüleri eklenecektir.*
> ![Sprint Board](./ProjectManagement/Sprint1Documents/sprintboard_sprint1.png)

### Ürün Durumu

> 📸 *Uygulama ekran görüntüleri eklenecektir.*
> ![Uygulama Ekranı 1](./ProjectManagement/Sprint1Documents/product_ss1.png)

### Sprint Review

**Katılımcılar:** [İsimler yazılacak]

**Tamamlanan Story'ler:**
- [x] Ofis kaydı + JWT auth
- [x] Multi-tenant RLS (docker-compose ile uçtan uca test edildi; superuser bypass, transaction-scoped context ve cross-tenant login sorunları tespit edilip düzeltildi — bkz. [TEKNIK_YOL_HARITASI.md](./TEKNIK_YOL_HARITASI.md))
- [x] Portföy CRUD (create + list)
- [x] Matching Agent MVP
- [x] GitHub Actions CI/CD (pytest + ruff, Postgres servisli)
- [ ] iyzico sandbox aktivasyon talebi — **manuel aksiyon gerekiyor**, henüz gönderilmedi
- [ ] WhatsApp Business doğrulama başvurusu — **manuel aksiyon gerekiyor**, henüz başlatılmadı
- [ ] Railway'e gerçek deploy — CI'da build/test var, henüz canlı deploy adımı yok

**Sonraki Sprint'e Devreden:**
iyzico sandbox aktivasyonu ve WhatsApp Business başvurusu kurumsal/manuel işlemler olduğu için Sprint 2'ye devrediyor; bu ikisi Sprint 2'nin ilk gününde paralel başlatılmalı (bkz. TEKNIK_YOL_HARITASI.md Bölüm 5). Railway deploy'u da Sprint 2 kapsamına alındı.

**Alınan Kararlar:**
RLS testinde ortaya çıkan üç güvenlik açığı (superuser bypass, SET LOCAL'in transaction-scoped olması, login'in cross-tenant sorgu ihtiyacı) kod incelemesiyle değil gerçek Docker ortamında uçtan uca test ederek bulundu — bundan sonraki her multi-tenant değişiklikte aynı testin (`backend/tests/test_rls.py`) CI'da çalışması zorunlu tutulacak.

### Sprint Retrospective

**Ne iyi gitti?**
[Buraya yazılacak]

**Ne geliştirilmeli?**
[Buraya yazılacak]

**Aksiyon Maddeleri:**
[Buraya yazılacak]

---

# Sprint 2

> 📅 **6 Temmuz — 19 Temmuz 2026**

### Backlog Düzeni ve Story Seçimleri

Sprint 2'de gerçek entegrasyonları (ödeme, WhatsApp) ve Pricing/Scoring ajanlarını tamamlamayı hedefliyoruz.

> ⚡ **Erken başlangıç notu (2 Temmuz 2026):** Sprint 1 kapanışının ardından, resmi Sprint 2 tarihi beklenmeden Pricing Agent, Scoring Agent ve Next.js ofis paneli story'leri kod tarafında tamamlandı ve uçtan uca doğrulandı (backend: 27/27 test yeşil; frontend: `next build` başarılı, CORS uçtan uca doğrulandı). Detaylar için [TEKNIK_YOL_HARITASI.md](./TEKNIK_YOL_HARITASI.md)'na bakınız.

**Planlanan Story'ler (Taslak):**

| # | User Story | Puan (Tahmini) |
|---|-----------|----------------|
| 6 | iyzico canlı ödeme akışı: ürün + 3 `pricingPlan` (Starter/Professional/Enterprise) | 8 |
| 7 | WhatsApp Business API başvurusu + BSP seçimi + Intake Agent webhook entegrasyonu | 8 |
| 8 | ✅ Pricing Agent: ChromaDB emsal embedding + k-NN benzerlik ile fiyat aralığı önerisi *(erken tamamlandı)* | 8 |
| 9 | ✅ Scoring Agent: kural bazlı skor motoru (yanıt hızı + mesaj sayısı + bütçe tutarlılığı) *(erken tamamlandı)* | 5 |
| 10 | ✅ Ofis paneli (Next.js): lead listesi + portföy yönetimi temel ekranları *(erken tamamlandı)* | 8 |

### Daily Scrum

> 📎 [Sprint 2 Daily Scrum Notları](./ProjectManagement/Sprint2Documents/DailyScrumNotes_Sprint2.md)

### Sprint Board Güncellemeleri

*Ekran görüntüleri eklenecektir.*

### Ürün Durumu

*Ekran görüntüleri eklenecektir.*

### Sprint Review

*Sprint bitiminde doldurulacaktır.*

### Sprint Retrospective

*Sprint bitiminde doldurulacaktır.*

---

# Sprint 3

> 📅 **20 Temmuz — 2 Ağustos 2026**

### Backlog Düzeni ve Story Seçimleri

Sprint 3'te hero özellikleri (Voice-to-Listing, Ulaşım Raporu, Otomatik Takip) canlıya almayı ve deployment/polish adımlarını hedefliyoruz.

**Planlanan Story'ler (Taslak):**

| # | User Story | Puan (Tahmini) |
|---|-----------|----------------|
| 11 | Voice-to-Listing: Whisper transkripsiyon + Gemini ile ilan taslağı, danışman onay adımı zorunlu | 8 |
| 12 | Markalı ulaşım/konum raporu: Google Maps Directions API + WeasyPrint PDF üretimi | 5 |
| 13 | Otomatik WhatsApp takip mesajı zinciri | 5 |
| 14 | Production deployment: Railway/Render + Sentry hata izleme + retry/timeout mekanizmaları | 5 |
| 15 | Onboarding'de zorunlu veri kalitesi kontrolü (eksik/tutarsız portföy girişini engelleme) | 3 |

### Daily Scrum

> 📎 [Sprint 3 Daily Scrum Notları](./ProjectManagement/Sprint3Documents/DailyScrumNotes_Sprint3.md)

### Sprint Board Güncellemeleri

*Ekran görüntüleri eklenecektir.*

### Ürün Durumu

*Ekran görüntüleri eklenecektir.*

### Sprint Review

*Sprint bitiminde doldurulacaktır.*

### Sprint Retrospective

*Sprint bitiminde doldurulacaktır.*

---

## Lisans

Bu proje YZTA Bootcamp 2026 kapsamında geliştirilmiştir. © Takım [151]
