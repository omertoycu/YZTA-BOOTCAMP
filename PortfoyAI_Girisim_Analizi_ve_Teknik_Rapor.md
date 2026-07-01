# PortföyAI — Girişim Analizi ve Teknik Yol Haritası Raporu

*Hazırlanma amacı: YZTA Bootcamp kapsamında geliştirilecek PortföyAI ürününü gerçek bir B2B SaaS girişimi olarak değerlendirmek; piyasadaki gerçek konumunu netleştirmek, satılabilir bir farklılaşma stratejisi kurmak ve uygulanabilir bir teknik yol haritası çıkarmak.*

---

## 0. Önce Dürüst Bir Uyarı: "Piyasada Az Muadili Var" İddiası Doğru Değil

README'de yer alan "Türkiye'deki emlak portalları sadece ilan barındırma yapıyor, AI-native bir araç yok" iddiasını doğrulamak için piyasayı taradım. Sonuç, projeyi zayıflatmıyor ama **konumlandırmayı kökten değiştirmesi gerekiyor.** Rakip yok değil — rakip var ve bir kısmı zaten aynı özellikleri sunuyor:

| Rakip | Ne sunuyor | PortföyAI ile çakışan alan |
|---|---|---|
| **Arveya CRM** | AI lead skorlama, makine öğrenmesiyle konum/bütçe/davranış eşleştirmesi, WhatsApp tetikleyici kampanyalar, explainable AI paneli | Scoring Agent, Matching Agent, WhatsApp otomasyonu — neredeyse birebir |
| **RE-OS** | "Türkiye'nin en gelişmiş AI destekli emlak CRM'i", akıllı değerleme, çok dilli AI içerik üretimi, MLS havuzu | Pricing Agent'a çok yakın bir "akıllı değerleme" özelliği |
| **Rapitek** | AI destekli satış + WhatsApp entegrasyonu, 2 haftada kurulum, 200+ uygulama deneyimi | Intake Agent'ın WhatsApp tarafı |
| **EmlakCRMx** | AI eşleştirme, skor motoru, portföy yönetimi | Matching + Scoring |
| **Bitrix24** | Ücretsiz CRM, çok kanallı lead toplama, otomasyon | Fiyat baskısı yapan "ücretsiz" alternatif |
| **Global**: Ylopo, Structurely, Lofty, CINC | 7/24 AI metin/sesli lead nitelendirme, canlı transfer, drip kampanya | Intake + Scoring Agent'ın uluslararası muadilleri (henüz TR'de yok ama gelme ihtimali yüksek) |

Bu, EmlakCRMx ve Arveya gibi oyuncuların 2025-2026'da emlak yazılımlarını veri depolayan araçlardan, veriyi işleyip danışmanı harekete geçiren bir "işletim sistemi"ne dönüştürdüğünü gösteriyor — yani "AI destekli emlak CRM'i" pazarlama cümlesi artık Türkiye'de sektör standardı, ayırt edici özellik değil.

**Sonuç:** "AI'lı emlak CRM'i" başlığıyla pazara girersen, zaten yerleşik, muhtemelen daha fazla sermayesi ve müşteri tabanı olan oyuncularla doğrudan fiyat/özellik savaşına girersin. Bootcamp değerlendirmesi açısından bu tehlikeli değil (hakem gerçek rakip analizini görmek ister), ama gerçek bir girişim olarak düşünüldüğünde **konumlandırmayı dar ve gerçekten boş olan bir nişe çekmek gerekiyor.**

### Gerçekten boş görünen alanlar

Araştırmada iki spesifik açık tespit ettim:

1. **Sesli not → ilan otomasyonu**: Hiçbir Türkiye rakibinde bu özelliği görmedim. Ancak dikkat: bir sektör kaynağı Türkçe sesli AI asistanların doğal dil işleme kalitesinin, gerçek saha konuşmalarını güvenilir şekilde yönetecek olgunluğa henüz ulaşmadığını belirtiyor — yani bu özellik **teknik risk taşıyan bir farklılaştırıcı**, garanti bir kazanç değil. Whisper transkripsiyonu + LLM temizleme kombinasyonuyla, düşük gürültülü saha ortamlarında (örn. sessiz araç içi not) MVP kalitesinde çalışabilir; gürültülü/kalabalık ortamda başarısız olur. Bunu net bir varsayım olarak işaretlemek ve erken kullanıcı testiyle doğrulamak gerekiyor.
2. **Markalı ulaşım/konum raporu (PDF)**: Rakip taramasında doğrudan bir muadiline rastlamadım. Google Maps Directions API ile üretilen, ofis logolu, kapanış aracı olarak kullanılan bir rapor gerçekten nadir. Bu, teknik olarak en kolay uygulanabilir ve en az rekabetçi özelliğiniz — **asıl "az muadili olan" iddiayı burada kanıtlayabilirsiniz.**

Ayrıca dikkat edilmesi gereken bir veri kalitesi gerçeği var: aynı kaynak, Türkiye'deki emlak danışmanlarının büyük bölümünün portföy bilgisini eksik girdiğini (fotoğrafsız, tahmini metrekare, muğlak bölge adı) ve bu zeminde eşleştirme/skor motorlarının güvenilmez sonuçlar ürettiğini aktarıyor. Bu, Matching ve Scoring Agent'larınızın gerçek dünyada karşılaşacağı en büyük engel; teknik mimariden önce çözülmesi gereken bir "veri girişi disiplini" sorunu.

---

## 1. Yeniden Konumlandırma Önerisi

"Bir emlak CRM'i daha" olmaktan çıkmak için tavsiye edilen odak: **"AI Matching + Scoring + CRM" yerine "AI Kapanış Asistanı."**

Rakiplerin hiçbiri lead'i nitelendirmekten kapanışa kadar tek bir anlatı kurmuyor. Önerilen konumlandırma:

> *PortföyAI, emlakçının CRM'i değil — emlakçının, ilk WhatsApp mesajından imzaya kadar hiçbir fırsatı kaçırmamasını sağlayan dijital asistanıdır.*

Bunun somut anlamı: **Voice-to-Listing + Ulaşım Raporu + Otomatik Takip Mesajı** üçlüsünü ürünün "hero" özellikleri yapın (bunlar rakiplerde yok), Matching/Scoring/Pricing'i ise "beklenen temel özellikler" (table stakes) olarak konumlandırın — var olmaları gerekiyor ama pazarlamanın merkezine onları koymayın, çünkü zaten herkes bunu söylüyor.

---

## 2. Hedef Kitle Daraltması ve Satış Stratejisi

### 2.1 İlk hedef: küçük ofisler, büyük zincirler değil

5-20 danışmanlı ofisler yerine **1-5 kişilik bireysel/mikro ofisleri** ilk hedef kitle yapmanızı öneririm. Sebep: büyük ofisler zaten Arveya/RE-OS gibi kurumsal satış süreçli, referanslı ürünlere bağlanmış durumda; onları değiştirmek uzun satış döngüsü ve güven inşası gerektirir. Bireysel emlakçı ise WhatsApp'ta manuel çalışıyor, değişim maliyeti düşük, 499 TL/ay fiyat noktası bu segment için mantıklı.

### 2.2 Somut GTM (Go-to-Market) taktikleri

- **Emlak ofisi WhatsApp grupları ve Facebook toplulukları** — Türkiye'de emlakçılar il/ilçe bazlı WhatsApp gruplarında yoğun. Organik erişim için en verimli kanal.
- **"14 gün sınırsız deneme + kurulum sırasında ilk 10 lead'i biz nitelendirelim" teklifi** — soğuk başlangıç sorununu (cold start) çözer, ürünün değerini ilk haftada gösterir.
- **Emlak odaları (TÜGEM, İstanbul Emlak Odası vb.) ile içerik/webinar iş birliği** — RE-OS'un emlak odalarıyla geliştirdiği modelin küçük ölçekli versiyonu.
- **Ulaşım/konum raporu örneğini ücretsiz "lead magnet" yapın** — bir emlakçının müşterisine göndereceği ilk markalı PDF'i ücretsiz üretin, ürünü hiç kullanmamış birine bile "işte bu senin işini nasıl kolaylaştırır" gösterin.
- **Referans komisyonu**: mevcut abone her yeni ofis getirdiğinde 1 ay ücretsiz — düşük CAC (müşteri edinme maliyeti) sağlar, B2B SaaS'ta klasik ve etkili bir taktik.

### 2.3 Fiyatlandırma üzerine not

README'deki üç kademeli model (Starter/Professional/Enterprise) makul, ama **Starter planın WhatsApp AI erişimini tamamen kesmesi** riskli — çünkü ürünün en çekici özelliği (Intake Agent) tam da bu planda yok. Öneri: Starter'a sınırlı sayıda WhatsApp AI mesajı (örn. ayda 100 konuşma) dahil edin, aşımda upsell tetiklensin. Bu hem "ücretsiz kullanım riskini mimari seviyede engelleme" hedefinizle uyumlu hem de deneme kullanıcısının gerçek değeri görmesini sağlar.

---

## 3. Teknik Maliyet Modeli (Gerçek Rakamlarla)

Bir SaaS'ı satmadan önce birim ekonomisini (unit economics) bilmeniz gerekir. Aşağıdaki rakamlar Temmuz 2026 itibarıyla güncel kaynaklardan derlendi:

### 3.1 LLM maliyeti (Gemini API)

Gemini modellerinin fiyatlandırması 3.5 Flash için 1M token başına 1,50$ girdi / 9$ çıktı, 2.5 Flash-Lite için ise 0,10$ / 0,40$ şeklindedir. Ayrıca Google, asenkron/gecikmesi önemli olmayan işler için Batch API'de tüm modellerde %50 indirim sunuyor — voice-to-listing gibi gerçek zamanlı olması gerekmeyen işler bu modelle çalıştırılmalı.

**Pratik öneri:** Intake/Matching/Scoring gibi yüksek hacimli, düşük karmaşıklıklı görevler için **Flash-Lite**, Pricing Agent gibi daha karmaşık emsal analizi gerektiren görevler için **Flash veya Pro** kullanın. Bir ofis ayda ~500 WhatsApp konuşması + 200 eşleştirme + 50 fiyat analizi yapıyorsa, aylık LLM maliyeti muhtemelen 150–400 TL bandında kalır — 499 TL'lik Starter fiyatının küçük bir kısmı, marj güvenli.

### 3.2 WhatsApp Business API maliyeti

Meta'nın 24 saatlik "konuşma" bazlı ücretlendirmesinde müşteri tarafından başlatılan Service konuşmalarında ilk 1000 konuşma her ay ücretsizdir; bu limit her ay yenilenir. Ofis tarafından başlatılan (proaktif takip mesajı gibi) konuşmalarda ise türe göre 0,15–0,40 TL arası ücret uygulanır. Bunun ötesinde bir **BSP (Business Solution Provider)** ücreti de vardır (WaMessage, Invekto, VatanSMS gibi Türkiye'deki sağlayıcılar aylık paket satıyor) — bunu Sprint 2 planlamasına bütçe kalemi olarak eklemelisiniz, README'de bu maliyet hiç geçmiyor.

**Önemli mimari uyarı:** Meta, WhatsApp Business Cloud API başvurularında iş doğrulaması (Business Verification) ve mesaj şablonu onayı istiyor; bu süreç günler sürebilir. Sprint 2'de "WhatsApp entegrasyonu" tek bir story olarak planlanmış (8 puan) — gerçekte bu, API başvurusu + BSP seçimi + şablon onayı + entegrasyon olmak üzere 3-4 ayrı iş kalemine bölünmeli, aksi halde sprint gecikir.

### 3.3 iyzico Abonelik Yönetimi maliyeti

iyzico'nun Abonelik Yönetimi kullanımı ücretlidir: ilk 3 ay ücretsiz, sonrasında aylık 199 TL'dir. Bu, sabit bir işletme gideri olarak modele eklenmeli. Teknik akış açısından: abonelik PENDING durumunda başlarsa veya bir deneme süresi tanımlıysa, iyzico sadece kart doğrulaması yapar (1 TL çekim + iade); gerçek tahsilat deneme bitince başlar — bu, README'deki "14 gün deneme, kredi kartı istemeden başlar" ifadesiyle çelişiyor. iyzico'nun sandbox/canlı akışında **kart bilgisi olmadan deneme başlatmak mümkün değil**, sadece "karttan para çekmeden deneme" mümkün. Pazarlama metnini "kredi kartı gerektirmez" yerine "deneme boyunca ücret alınmaz" şeklinde düzeltmeniz gerekiyor, yoksa teknik gerçekle pazarlama vaadi çelişir.

---

## 4. Teknik Yol Haritası — Detaylı ve Araç Bazlı

Aşağıdaki plan, README'deki sprint yapısını korur ama her story'yi "hangi araçla, nasıl" seviyesinde somutlaştırır ve gerçekçi olmayan tahminleri düzeltir.

### Sprint 1 (19 Haz – 5 Tem): Temel İskelet

| Story | Araç / Yöntem | Not |
|---|---|---|
| Ofis kaydı + auth | FastAPI + JWT, `python-jose` veya `Authlib` | RBAC şemasını en baştan (ofis sahibi/ajan/görüntüleyici) DB seviyesinde tasarlayın |
| Multi-tenant RLS | PostgreSQL `CREATE POLICY` + `office_id` kolonu her tabloda + `SET app.current_office_id` session değişkeni | Supabase kullanmıyorsanız RLS'i FastAPI middleware'inde her request'te set etmeyi unutmayın — en sık atlanan adım budur |
| Manuel ilan ekleme | SQLAlchemy modeli + basit REST CRUD | Bu aşamada AI yok, sade form |
| Matching Agent MVP | LangGraph'te tek node, basit filtre (bütçe aralığı + oda sayısı + bölge) — henüz vektör benzerliği değil | 8 puan gerçekçi, ama "gerçek zamanlı" ifadesini "senkron API çağrısı" olarak okuyun, gerçek zamanlı stream değil |
| iyzico sandbox | iyzico Türkiye resmi sandbox ortamı, `entegrasyon@iyzico.com`'a mail atarak abonelik özelliğini aktive ettirme gerekiyor — bu adım README'de yok, süre kaybettirebilir | Bu maili Sprint 1'in ilk günü atın, onay süresi belirsiz |
| CI/CD | GitHub Actions + Railway otomatik deploy | — |

**Gerçekçi puan düzeltmesi:** iyzico sandbox aktivasyonu manuel onay gerektirdiği için Sprint 1'in ilk gününde talep edilmeli; aksi halde Sprint 1 sonunda "test ödemesi alınabilmeli" story'si bloke olur.

### Sprint 2 (6 – 19 Tem): Gerçek Entegrasyonlar

- **iyzico canlı ödeme**: `v2/subscription/products` → `pricingPlans` → `checkoutform/initialize` akışı. Ürün ve planlar API veya panel üzerinden oluşturulur; her ödeme planı en az bir ürüne bağlı olmak zorundadır. Starter/Professional/Enterprise için 3 ayrı "ürün" değil, tek ürün + 3 farklı `pricingPlan` kurun (yönetimi kolaylaştırır).
- **WhatsApp entegrasyonu**: Meta Business Manager doğrulaması + bir BSP seçimi (kendi başvurunuz onaylanana kadar VatanSMS/Invekto gibi bir sağlayıcı üzerinden başlamak hız kazandırır) + LangGraph'te webhook → Intake Agent node.
- **Pricing Agent**: ChromaDB'de bölgesel emsal ilan embedding'leri (Gemini `text-embedding-004` ile), k-NN benzerlik + basit istatistiksel aralık hesaplama. Gerçek bir "AI fiyat tahmini" değil, "benzer ilan aralığı" olarak konumlandırın — daha az risk, daha savunulabilir bir iddia.
- **Scoring Agent**: İlk versiyonda ML modeli değil, kural bazlı skor (yanıt hızı + mesaj sayısı + bütçe tutarlılığı ağırlıklı toplam) yeterli. Gerçek ML modeli için yeterli etiketli veri (dönüşen/dönüşmeyen lead) biriktirmeden LLM'e "skorla" dedirmek güvenilmez sonuç üretir — bu konuda rakip kaynağı da veri kalitesi uyarısı yapıyor.

### Sprint 3 (20 Tem – 2 Ağu): Farklılaştırıcı Özellikler + Canlıya Alma

- **Voice-to-Listing**: Whisper API (OpenAI) ile transkripsiyon → Gemini ile ilan metni. **Riski azaltmak için**: MVP'de sadece net, sessiz ortam kaydı hedefleyin; gürültü azaltma (noise reduction) sonraki faza bırakılabilir. Kullanıcıya "düzenle ve onayla" adımı zorunlu olsun — AI çıktısını doğrudan yayınlamayın.
- **Ulaşım/konum raporu**: Google Maps Directions API + WeasyPrint. Bu, en düşük teknik riskli ve pazarlanabilirliği en yüksek özellik — demo videosunda öne çıkarın.
- **Deployment**: Railway/Render + PostgreSQL managed instance + ortam değişkenleri için Doppler veya Railway'in kendi secret yönetimi.
- **Performans/hata yönetimi**: LangGraph node'larına retry + timeout ekleyin (LLM çağrıları zaman zaman başarısız olur); Sentry gibi bir hata izleme aracı entegre edin — README'de bu adım yok, production için kritik.

---

## 5. Riskler ve Azaltma Stratejileri

| Risk | Etkisi | Azaltma |
|---|---|---|
| Piyasada zaten AI'lı emlak CRM'leri var (Arveya, RE-OS) | Farklılaşma zayıflar, fiyat rekabetine girilir | Bölüm 1'deki yeniden konumlandırmayı uygulayın: hero özellik Voice-to-Listing + Ulaşım Raporu |
| Türkçe sesli AI'nın saha koşullarında güvenilirliği düşük | Voice-to-Listing kullanıcı güvenini kırabilir | MVP'de "AI taslak üretir, danışman onaylar" akışını zorunlu tutun, asla otomatik yayınlamayın |
| Emlakçıların portföy verisi eksik/tutarsız | Matching/Scoring yanlış sonuç üretir, "sistem çalışmıyor" algısı oluşur | Onboarding'de zorunlu alan kontrolü + veri kalitesi rehberi (rakiplerin de yaptığı gibi) |
| WhatsApp Business API onay süreci öngörülemez | Sprint 2 gecikebilir | Başvuruyu Sprint 1'in sonunda başlatın, geçici bir BSP ile paralel ilerleyin |
| iyzico abonelik aktivasyonu manuel onaya bağlı | Sprint 1 ödeme story'si bloke olabilir | Talebi Sprint 1 gün 1'de gönderin |
| "Kredi kartsız deneme" vaadi teknik gerçekle çelişiyor | Pazarlama/ürün tutarsızlığı, güven kaybı | Metni "deneme boyunca ücretsiz, kart bilgisi doğrulama için istenir" olarak netleştirin |

---

## 6. Özet Öneriler (Aksiyon Listesi)

1. README'deki "piyasada az muadili var" cümlesini kaldırın veya "AI destekli emlak CRM'i kategorisinde rekabet var, ama uçtan uca sesli not→ilan ve markalı ulaşım raporu kombinasyonu benzersizdir" şeklinde düzeltin — jüri/hakem karşısında bunu bilerek sunmak, bilmeden sunmaktan çok daha güçlü bir izlenim bırakır.
2. Pazarlama ve demo anlatısını Matching/Scoring'den Voice-to-Listing + Ulaşım Raporu'na kaydırın.
3. Sprint 1'in ilk gününde iyzico abonelik aktivasyon talebini ve WhatsApp Business doğrulama sürecini paralel başlatın.
4. Fiyatlandırma metnini teknik gerçekle uyumlu hale getirin (kart doğrulama notu).
5. Starter plana sınırlı WhatsApp AI kotası ekleyin ki deneme kullanıcısı gerçek değeri görebilsin.
6. İlk hedef kitleyi 1-5 kişilik bireysel ofislere daraltın, WhatsApp grupları ve emlak odası iş birlikleriyle organik büyüyün.

---

*Not: Bu rapor kamuya açık web kaynaklarından Temmuz 2026 itibarıyla derlenmiştir; fiyatlar ve API koşulları değişebilir, uygulama öncesi ilgili sağlayıcıların (Meta, iyzico, Google) güncel dokümantasyonu kontrol edilmelidir.*
