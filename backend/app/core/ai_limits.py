"""Gemini çağrılarının max_output_tokens tavanları — tek yerden ayarlanır.

Katmanlı yaklaşım: serbest metin üreten çağrılar (WhatsApp yanıt taslağı,
piyasa özeti) kısa tutulur — çıktı token'ı doğrudan maliyettir ve WhatsApp'ta
uzun mesaj zaten istenmez. JSON dönen çağrılara ise kesilmeyi (truncated JSON
→ parse hatası → özellik bozulur) önleyen daha yüksek tavanlar verilir;
özellikle sesli not çağrıları birebir transkript döndürdüğü için en geniş
tavana ihtiyaç duyar.

DİKKAT: gemini-2.5-flash bir "thinking" model — max_output_tokens iç düşünme
token'larını da kapsayabilir. Tavan çok sıkılırsa model hiç görünür metin
üretemeden kesilir (boş response.text → mevcut hata yolları devreye girer,
bot deterministik listeye düşer). REPLY_DRAFT bu yüzden 200'ün altına
İNDİRİLMEMELİ; boş yanıt oranı artarsa ilk ayar noktası burası.
"""

# Serbest metin: WhatsApp yanıt taslağı (app/agents/reply_draft.py) —
# prompt zaten "en fazla 3 kısa cümle" istiyor, tavan güvenlik ağı.
MAX_TOKENS_REPLY_DRAFT = 200

# Serbest metin: web araştırmalı fiyat kontrolü (app/agents/market_price_check.py) —
# 3 satırlık sabit format + 1-2 cümlelik özet.
MAX_TOKENS_MARKET_PRICE_CHECK = 256

# Serbest metin: konuşma özeti (app/agents/lead_summary.py) — tek cümle
# istenir, tavan yine thinking payı bırakır (yukarıdaki uyarı).
MAX_TOKENS_CONVERSATION_SUMMARY = 200

# JSON: WhatsApp mesajından alan çıkarımı (app/agents/whatsapp_extract.py) —
# şema küçük (7 alan) ama kesilirse parse hatası olur, rahat bir tavan.
MAX_TOKENS_EXTRACTION = 512

# JSON: eşleşme yeniden sıralama (app/agents/match_ranking.py) — aday sayısı
# değişken, her aday için index+skor+15 kelimelik gerekçe.
MAX_TOKENS_RERANK = 1024

# JSON + birebir transkript: sesli ilan / sesli CRM notu (app/agents/
# voice_listing.py, lead_voice_note.py) — birkaç dakikalık kaydın transkripti
# uzun olabilir, kesilirse tüm taslak çöpe gider.
MAX_TOKENS_VOICE = 4096
