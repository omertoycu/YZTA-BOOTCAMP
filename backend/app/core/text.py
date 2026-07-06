def fold_turkish_i(text: str) -> str:
    """Python'un str.lower()'ı Türkçe büyük "İ"yi TEK bir küçük harfe değil,
    "i" + görünmez bir COMBINING DOT ABOVE karakterine ayırır (Unicode'un
    varsayılan, yerel-ayardan bağımsız case-folding kuralı) — bu da
    "KİRALIK".lower()'ı "kiralik" değil "ki̇ralik" yapıp bir alt-dize aramasını
    sessizce kırar (gerçek prod hatası, bkz. listing_import.py). Çözüm:
    İ/I/ı'nın hepsini büyük/küçük harf farkı önemsemeden düz "i"ye indirip
    sonra normal .lower() uyguluyoruz."""
    return text.replace("İ", "i").replace("I", "i").replace("ı", "i").lower()
