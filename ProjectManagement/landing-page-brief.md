# PortföyAI — Landing Page Tasarım Brief'i

## Ürün Tek Cümlede

PortföyAI, emlak danışmanlarının WhatsApp'tan gelen hiçbir müşteriyi kaçırmadan doğru alıcıyı doğru portföyle buluşturmasını sağlayan bir yapay zeka asistanı. Klasik bir CRM değil; danışmanın günlük işini (ilan girmekten müşteri takibine kadar) hızlandıran bir yardımcı.

## Hedef Kitle

- 1–5 danışmanlı bağımsız emlak ofisleri
- Hâlâ WhatsApp ve Excel ile manuel çalışan, dijitalleşmemiş emlak danışmanları
- İlan girme ve müşteri takibinde en çok zaman kaybeden, sahada çalışan danışmanlar

## Ton ve Dil

- Sade, anlaşılır, profesyonel — teknik jargon yok (danışman kitlesi yazılımcı değil)
- Somut, günlük hayattan örnekler tercih edilsin ("arabada müşteriyle gezerken konuşup ilan oluşturmak" gibi)
- Abartılı pazarlama dili yok; güven veren, sakin bir kurumsal ton

## Tasarım Sistemi (mevcut üründen — birebir uygulanmalı)

- **Renkler:** Ana vurgu rengi siyah (`#000000`), ikincil/marka rengi mint-teal (`#006875`), açık mint arka plan (`#E0F2F1`). Nötr yüzeyler açık gri tonları (`#f3f4f5`, `#edeeef`, `#e1e3e4`).
- **Tipografi:** Başlıklar için Plus Jakarta Sans, gövde metni/etiketler için Inter.
- **İkonlar:** Material Symbols Outlined (mevcut ürün panelinde kullanılıyor).
- **Genel his:** Bento-grid / kart tabanlı düzen, yuvarlatılmış köşeler, yumuşak gölgeler — mevcut ürün panelinin (`/dashboard`, `/listings`) görsel diliyle tutarlı olmalı.

## Sayfa Bölümleri (yukarıdan aşağıya)

1. **Hero**
   - Başlık: "İlk WhatsApp mesajından imzaya kadar hiçbir fırsatı kaçırmayın"
   - Alt başlık: PortföyAI'nin ne olduğunu 1-2 cümlede özetleyen metin (yukarıdaki "Ürün Tek Cümlede" bölümü)
   - CTA butonu: "Ücretsiz Dene" / "Demo İste"
   - Görsel: Ürünün gerçek arayüzünden bir ekran görüntüsü ya da mockup (dashboard/portföy kartları)
   - Scroll animasyonu: Hafif fade-in + yukarı kayma; sayfa yüklenince hemen görünür, scroll'a bağımlı olmasın

2. **Sorun / Çözüm**
   - Kısa bir karşılaştırma: "Bugün nasıl çalışıyorsunuz?" (WhatsApp'ta kaybolan mesajlar, Excel'de dağınık takip) vs "PortföyAI ile nasıl olacak?"
   - Scroll animasyonu: İki kart yan yana, scroll ile sırayla belirsin (stagger fade-in)

3. **Öne Çıkan Özellikler** (rakiplerde olmayan, ürünün asıl farkı — 3 kart)
   - 🎙️ **Sesli Not → İlan**: Danışman telefonuna konuşur, yapay zeka dinleyip ilan taslağını (başlık, bölge, fiyat, oda sayısı, m²) otomatik hazırlar.
   - 🗺️ **Markalı Ulaşım/Konum Raporu**: Hedef adres girilir, araç/yürüyüş/toplu taşıma süreleri hesaplanıp ofis logolu bir PDF rapor oluşturulur.
   - 💬 **Otomatik WhatsApp Takip Zinciri**: "Otomatik Takip" açıldığında sistem müşteriye giderek yumuşayan hatırlatma mesajları gönderir; müşteri yanıt verince zincir otomatik durur.
   - Scroll animasyonu: Her kart scroll ile sırayla sahneye girsin (yukarıdan/soldan kayarak + fade-in), sticky bir başlıkla eşlik edebilir

4. **Nasıl Çalışır?** (3-4 adımlı basit akış)
   - Örn: 1) Portföyünü ekle (sesle/formla/yapıştırarak) → 2) Müşteri WhatsApp'tan yazar → 3) Sistem otomatik puanlar ve eşleştirir → 4) Danışman takibi hiç unutmaz
   - Scroll animasyonu: Yatay/dikey bir zaman çizelgesi, scroll ile adımlar sırayla aydınlansın (progress-line dolarak ilerlesin)

5. **Temel Özellikler** (sektör standardı ama olmazsa olmaz — kısa ikon+başlık listesi, kart değil, daha kompakt)
   - Müşteri Kaydı, İlan İçe Aktarma, Eşleştirme, Puanlama, Fiyat Önerisi, Raporlama, Çoklu Ofis Desteği, Abonelik/Faturalama
   - Scroll animasyonu: Basit fade-in grid, abartılı olmasın (bu bölüm destekleyici, hero değil)

6. **Hedef Kitle / Kimler İçin?**
   - 1-5 danışmanlı ofisler, hâlâ WhatsApp+Excel ile çalışanlar vurgusu
   - Scroll animasyonu: Minimal, sade fade-in

7. **CTA / Kapanış**
   - Net bir çağrı: "Ofisiniz için PortföyAI'yi bugün deneyin"
   - İletişim/demo talep formu ya da buton
   - Scroll animasyonu: Belirgin, dikkat çekici bir son vurgu (örn. arka plan rengi mint'e dönsün)

## Teknik Notlar

- Sonradan gerçek üründe (Next.js 16 + Tailwind) kullanılacağı için, tasarımın bu yığına makul şekilde taşınabilir olması iyi olur (aşırı karmaşık/özel animasyon kütüphanelerinden kaçının; CSS/Framer Motion seviyesinde kalsın).
- Responsive olmalı — mobilde emlak danışmanları çoğunlukla telefondan bakacak.
- Sahte/uydurma istatistik veya müşteri yorumu KOYMAYIN — ürün henüz canlıya yeni alındı, gerçek olmayan sosyal kanıt kullanılmamalı.
