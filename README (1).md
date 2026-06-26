# Takım İsmi
## Takım [X] — EvRadar

---

# Ürün İle İlgili Bilgiler

## Takım Elemanları

| İsim | Rol |
|------|-----|
| [İsim Soyisim] | Product Owner |
| [İsim Soyisim] | Scrum Master |
| [İsim Soyisim] | Developer |
| [İsim Soyisim] | Developer |
| [İsim Soyisim] | Developer |

---

## Ürün İsmi

**EvRadar** — Akıllı Emlak ve Konum Eşleştirme Asistanı

---

## Ürün Açıklaması

EvRadar, kiralık ev arayışını kullanıcının bütçesi, günlük ulaşım rotaları ve kişisel yaşam tarzı tercihleriyle çapraz analiz eden otonom bir yapay zeka asistanıdır.

Kullanıcı sadece "İzmit'te 2+1, işe 45 dakikadan az, bütçem 12.000 TL" yazmak yeterlidir. EvRadar'ın çok ajanlı (multi-agent) mimarisi; Sahibinden, Hepsiemlak ve Emlakjet gibi platformlardaki ilanları toplar, her ev için Google Maps API üzerinden gerçek zamanlı ulaşım süresi ve maliyeti hesaplar, bütçeyi kira + aylık ulaşım toplamı olarak değerlendirir. Kullanıcının "bu ev çok gürültülü" ya da "metro yürüme mesafesi önemli" gibi doğal dil geri bildirimlerini hafıza ajanı aracılığıyla saklayan sistem, sonraki aramalarda bu tercihleri otomatik olarak uygular. Sonuç: evlerin salt kira değil, **toplam yaşam maliyeti** üzerinden sıralandığı kişiselleştirilmiş bir öneri motoru.

---

## Ürün Özellikleri

### Temel Özellikler
- 🔍 **Doğal Dil Arama** — "İzmit'te 2+1, metrobüse 10 dakika, 10.000 TL altı" gibi serbest metin sorguları LLM tarafından ayrıştırılır; oda sayısı, bütçe, lokasyon ve ulaşım koşulları otomatik çıkarılır
- 🏠 **Çok Kaynaklı İlan Toplama** — Listing Ajanı, Sahibinden / Hepsiemlak / Emlakjet ilanlarını gerçek zamanlı olarak toplar ve normalleştirir; yinelenen ve bayat ilanlar filtrelenir
- 🗺️ **Ulaşım Maliyeti Hesaplama** — Konum Ajanı, her ilan için kullanıcının iş/okul adresine alternatif rotalar (metro, otobüs, paylaşımlı scooter) hesaplar; günlük süre ve aylık taşıma maliyetini çıkarır
- 💰 **Toplam Yaşam Maliyeti Skoru** — Bütçe Ajanı, kira + aylık ulaşım maliyetini birleştirerek gerçek "cepten çıkacak" rakamı hesaplar ve bütçe aşımını önceden uyarır
- 🧠 **Hafızalı Öneri Sistemi** — Hafıza Ajanı, "bu ev çok eski", "asansör şart", "gürültülü cadde olmasın" gibi doğal dil geri bildirimlerini ChromaDB'de vektör olarak saklar; bir sonraki aramada bu kısıtlar otomatik devreye girer
- 🏆 **Ağırlıklı Öneri Motoru** — Her ilan için 0–100 arası bileşik puan hesaplanır: ulaşım skoru + bütçe skoru + tercih uyum skoru + konum kalite skoru
- 📍 **Harita Görselleştirme** — Folium tabanlı interaktif harita üzerinde önerilen evler ve her ev için işyerine giden rota gösterilir
- 💬 **Sohbet Arayüzü** — Streamlit chat widget'ı ile ajan sonuçları, sıralamalar ve harita tek ekranda sunulur

### Fark Yaratan Özellikler
- **Gerçek ulaşım süresi:** Google Maps Directions API ile trafik saatine göre gerçek süre (sabah rush hour'da kaç dakika?)
- **Toplu taşıma + yürüme kombinasyonu:** "Metrobüse yürüyerek 8 dk, metrobüste 22 dk, işyerine yürüyerek 5 dk — toplam 35 dk" formatında detaylı bilgilendirme
- **Aylık maliyet karşılaştırması:** 9.000 TL kirası olan ama 1.200 TL ulaşım masrafı çıkan ev mi, yoksa 10.000 TL kirası olan ama 300 TL ulaşımla iş başına giden ev mi daha avantajlı? EvRadar bunu hesaplar.
- **Tercih öğrenimi:** İlk aramada "asansör yok diyorum", sonraki aramada sistem asansörü default filtre olarak uygular

---

## Hedef Kitle

- Yeni bir şehre taşınan ya da ev değiştiren çalışanlar ve öğrenciler (18–40 yaş)
- İş değiştirip yeni konuma göre ev arayan profesyoneller
- İzmit, Kocaeli, İstanbul, Ankara gibi büyük şehirlerde kiralık ev arayanlar
- Ulaşım maliyetini kira kararına dahil etmek isteyen bütçe odaklı kullanıcılar
- Yabancı dil bilerek Türkiye'de ev arayan expat'lar (İngilizce destek eklenebilir)

---

## Kullanılan Teknolojiler

| Katman | Teknoloji | Gerekçe |
|--------|-----------|---------|
| LLM | Google Gemini Pro API | Doğal dil ayrıştırma, geri bildirim analizi |
| Agent Framework | LangChain + LangGraph | Çok ajanlı orkestrasyon ve durum yönetimi |
| Vektör DB | ChromaDB | Kullanıcı tercihlerinin embedding olarak saklanması |
| Veri Toplama | Playwright + BeautifulSoup | Sahibinden / Hepsiemlak / Emlakjet ilanları |
| Rota API | Google Maps Directions API | Gerçek zamanlı ulaşım süresi ve modu hesaplama |
| Backend | Python 3.11 + FastAPI | REST API ve ajan koordinasyon katmanı |
| Frontend | Streamlit | Sohbet arayüzü + Folium harita entegrasyonu |
| Harita | Folium + Leaflet.js | İnteraktif ev ve rota görselleştirmesi |
| Veritabanı | PostgreSQL | İlanlar, kullanıcı oturumları, tercih geçmişi |
| Deployment | Railway / Render | Ücretsiz katmanlı, anında deploy |
| Versiyon Kontrolü | GitHub | Tüm sprint belgeleri burada |

---

## Ajan Mimarisi

```
Kullanıcı Girişi (Doğal Dil)
        │
        ▼
┌─────────────────────┐
│ LangGraph           │
│ Orchestrator        │  ← Sorguyu ayrıştırır, ajanları yönlendirir
└──┬──────┬───────┬───┘
   │      │       │
   ▼      ▼       ▼
[Listing] [Konum] [Hafıza]  ← Paralel çalışır
  Ajanı   Ajanı   Ajanı
   │      │       │
   └──────┴───────┘
           │
           ▼
  ┌─────────────────┐
  │  Öneri Motoru   │  ← Bileşik skor hesaplar, sıralar
  └────────┬────────┘
           │
           ▼
  Kullanıcı Paneli & Harita
```

**Listing Ajanı:** Sahibinden/Hepsiemlak/Emlakjet'ten ilanları çeker, normalize eder, filtreler (oda sayısı, bütçe, ilçe)

**Konum Ajanı:** Her ilan için Google Maps Directions API çağrısı yapar; toplu taşıma ve yürüyerek süre + maliyet hesaplar

**Hafıza Ajanı:** ChromaDB üzerinde kullanıcı tercihlerini embedding olarak saklar; yeni sorgularda ilgili kısıtları geri çeker

**Öneri Motoru:** Üç ajandan gelen verileri birleştirerek ağırlıklı skor üretir:
- Ulaşım skoru (30%): sürece ve maliyete göre ters orantılı
- Bütçe skoru (40%): toplam maliyet / kullanıcı bütçesi
- Tercih uyum skoru (30%): hafıza ajanından gelen kısıt eşleşmesi

---

## Product Backlog URL

[📋 GitHub Projects — EvRadar Backlog](https://github.com/[KULLANICI-ADI]/evradar/projects/1)

> *Alternatif: [Miro Backlog Board](#)*

---

# Sprint 1

> 📅 **19 Haziran — 5 Temmuz 2026**
> Sprint puanı hedefi: `[Toplam puan]`

### Backlog Düzeni ve Story Seçimleri

Sprint 1'de ürünün temel iskeletini kurmayı hedefliyoruz: veri akışı, ajan çerçevesi ve temel UI. Bu sprintte ürünün "çalışan ama minimal" versiyonuna ulaşmayı planlıyoruz.

**Sprint 1 User Story'leri (Önerilen):**

| # | User Story | Puan |
|---|-----------|------|
| 1 | Kullanıcı olarak doğal dil ile "İzmit'te 2+1, 10.000 TL altı" yazabilmeliyim | 8 |
| 2 | Sistem, Hepsiemlak'tan 20+ ilanı listeleyebilmeli | 5 |
| 3 | Her ilan için Google Maps API'den tahmini ulaşım süresi çekilebilmeli | 8 |
| 4 | Temel Streamlit arayüzü üzerinde ilan listesi gösterilebilmeli | 3 |
| 5 | LangGraph Orchestrator temel yapısı ve Query Parser Ajanı kurulmalı | 5 |
| 6 | GitHub repo yapısı ve CI/CD pipeline kurulmalı | 2 |

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
- [ ] Doğal dil sorgusu ayrıştırma
- [ ] Hepsiemlak ilan çekme
- [ ] Google Maps API bağlantısı
- [ ] Temel Streamlit UI
- [ ] LangGraph Orchestrator iskelet
- [ ] GitHub repo yapısı

**Sonraki Sprint'e Devreden:**
[Buraya yazılacak]

**Alınan Kararlar:**
[Buraya yazılacak]

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

Sprint 2'de Hafıza Ajanı ve çok kaynaklı ilan toplama özelliklerini tamamlamayı hedefliyoruz.

**Planlanan Story'ler (Taslak):**

| # | User Story | Puan (Tahmini) |
|---|-----------|----------------|
| 7 | Kullanıcı "bu ev çok gürültülü" yazabilmeli, sistem bir sonraki aramada bunu hatırlamalı | 8 |
| 8 | Sahibinden.com ilanları listeye eklenebilmeli | 5 |
| 9 | Her ilan için "aylık toplam maliyet = kira + ulaşım" hesaplanabilmeli | 5 |
| 10 | Harita üzerinde önerilen evler ve rota gösterilebilmeli (Folium) | 8 |
| 11 | Bileşik skor hesaplama algoritması çalışır hale gelmeli | 5 |

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

Sprint 3'te deployment, polish ve değerlendirme kriterlerine yönelik ek AI özellikleri hedefliyoruz.

**Planlanan Story'ler (Taslak):**

| # | User Story | Puan (Tahmini) |
|---|-----------|----------------|
| 12 | Sistem Railway/Render üzerinden canlıya alınabilmeli | 5 |
| 13 | Kullanıcı tercih geçmişini görüntüleyip silebilmeli | 3 |
| 14 | "Sabah rush hour'da süre kaç dakika?" sorusunu yanıtlayabilmeli | 5 |
| 15 | AI tabanlı skor açıklaması: "Bu evi öneriyoruz çünkü..." | 8 |
| 16 | Performans optimizasyonu ve hata yönetimi | 3 |

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

Bu proje YZTA Bootcamp 2026 kapsamında geliştirilmiştir. © Takım [X]
