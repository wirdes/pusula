# Ölçüm sonuçları

| Dosya | İçerik |
|---|---|
| [`baseline.md`](baseline.md) | **Asıl ölçüm.** Kart metni: başlık, özet, adımlar. |
| [`baseline_with_keywords.md`](baseline_with_keywords.md) | Anahtar kelimeler eklenmiş hali. Test sorularıyla örtüştüğü için **iyimser**; karşılaştırma dışında kullanmayın. |

Ayrıntılı, soru bazında sonuçlar (`*.json`) betik her çalıştığında yeniden üretilir ve repoya eklenmez.

## İlk ölçüm (2026-10-23)

24 taslak kart, 136 soru (16'sı kapsam dışı). PC işlemcisinde, internet kapalıyken (`--offline`) ölçüldü.

| Model | Parametre | hit@1 | hit@3 | Kapsam dışı AUROC |
|---|---|---|---|---|
| ModernBERT-TR-Embed | 149M | **%75** | **%95** | **0,95** |
| bge-m3 (üst sınır) | 568M | %72 | %91 | 0,90 |
| multilingual-e5-small | 118M | %61 | %79 | 0,82 |
| BM25 + 5 harf kökü | – | %52 | %72 | 0,78 |

### Öne çıkanlar

1. **En iyi model Türkçeye özel olan.** 149M'lik ModernBERT-TR-Embed, neredeyse dört kat büyük çok dilli bge-m3'ü geçiyor. Doğru kart %95 oranında ilk üçte. Yani kısa vadede ekranda ilk üç kartı göstermek işe yarar.
2. **Kapsam dışı soruları ayırmak mümkün görünüyor.** AUROC 0,95; benzerlik skoruna bir eşik koyarak "bu konuda bilgim yok" demek uygulanabilir.
3. **Zayıf noktalar:** Türkçe karaktersiz yazım (%70), panik halindeki çok kısa sorular (%57), durumu dolaylı anlatan ve konuşma diline yakın sorular (%60).

### Güvenlik açısından kritik hatalar

Bazı hatalar sadece "yanlış kart" değil, **tam tersi talimat** anlamına geliyor:

- "nefes almıyor", "babam yere düştü nefes almıyor" gibi üç soru, **kalp masajı** yerine **"nefes alıyorsa yan yatır"** kartına gitti. Bu iki kart birbirine çok benziyor ama talimatları zıt.
- "Enkaz altında kaldım" gibi üç soru, kişinin **kendisi** için olan kart yerine **başkasına yardım** kartına gitti.

Bundan çıkan ders: Hayati ve birbirine benzeyen durumlar ayrı kartlar olarak aramaya bırakılmamalı. Örneğin "bilinci yok" tek bir akışa yönlendirilip kullanıcıya "Nefes alıyor mu?" diye **sorulmalı**. Arama doğru akışı bulur, karar ise evet/hayır sorusuyla verilir.

### Sonraki adımlar

1. Bilinç ve nefes kartlarını, kullanıcıya soru soran tek bir karar akışında birleştirmek.
2. Gerçek insanların, kartları görmeden yazdığı ayrı bir test seti toplamak. Şu anki sorular kartlarla aynı yazar tarafından yazıldı.
3. Türkçe karaktersiz girdiler için diakritik düzeltmeyi ya da eğitim verisinde bu tür örnekleri denemek.
4. Pusula'nın kendi modeli: ModernBERT-TR-Embed'i öğretmen olarak kullanıp telefona uygun 20–60M'lik bir öğrenci modeli eğitmek. Eğitim verisinde "kendim / başkası" ve "nefes alıyor / almıyor" gibi zor ayrımlar özellikle yer almalı.

### Sınırlamalar

- Sorular ve kartlar aynı yazar (Claude) tarafından yazıldı; gerçek kullanıcı sorularında sonuçlar daha düşük olabilir.
- Kartlar taslak; içerik değiştikçe sonuçlar da değişir.
- Süreler PC işlemcisinde ölçüldü, iPhone'daki hız ayrıca ölçülmeli.
