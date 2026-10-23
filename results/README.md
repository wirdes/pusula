# Ölçüm sonuçları

| Dosya | İçerik |
|---|---|
| [`baseline.md`](baseline.md) | **Asıl ölçüm.** Kart metni: başlık, özet, adımlar. |
| [`baseline_with_keywords.md`](baseline_with_keywords.md) | Anahtar kelimeler eklenmiş hali. Test sorularıyla örtüştüğü için **iyimser**; karşılaştırma dışında kullanmayın. |

Ayrıntılı, soru bazında sonuçlar (`*.json`) betik her çalıştığında yeniden üretilir ve repoya eklenmez. `baseline.md` her zaman en son ölçümü gösterir; aşağıdaki bölümler ölçümlerin geçmişini özetler.

## İkinci ölçüm: hayatta kalma ve tehlike kartları (2026-10-23)

14 yeni kart eklendi (karbonmonoksit, doğada kaybolma, ateş yakma, barınak, su bulma, yön bulma, bilinmeyen bitki ve mantar, yılan ve akrep, arı sokması ve alerji, sıcak çarpması, yıldırım, orman yangını, sel, kar fırtınasında araçta mahsur kalma). Toplam 38 kart, 214 soru (24'ü kapsam dışı). Yeni sorular, sızıntıyı önlemek için kartların anahtar kelimelerinden bağımsız yazıldı.

| Model | Parametre | hit@1 | hit@3 | Kapsam dışı AUROC |
|---|---|---|---|---|
| ModernBERT-TR-Embed | 149M | **%75** | **%95** | **0,93** |
| bge-m3 (üst sınır) | 568M | %69 | %92 | 0,88 |
| multilingual-e5-small | 118M | %61 | %76 | 0,76 |
| BM25 + 5 harf kökü | – | %57 | %70 | 0,73 |

- Kart sayısı %58 arttı ama en iyi modelin başarısı korunuyor. Eski kartların sorularında ilk sıradan isabet %75'ten %73'e indi (karışabilecek kart sayısı arttı); yeni kartların sorularında %79 / %95–97.
- **Yeni kritik hata:** "sıcaktan başı dönüyor kusuyor" gibi sıcak çarpması sorularının 3'ü **hipotermi** kartına gitti. Biri serinletmeyi, diğeri ısıtmayı söylüyor; yine zıt talimat.
- Benzer konular birbirine karışıyor: bina yangını ile orman yangını, ateş yakma ile yangın, akrep ile arı sokması.
- Tek kelimelik panik sorgular hâlâ en zayıf tip (%40). Örneğin "YILAN" sorusu yardım işareti kartına gitti.

Zıt talimatlı kart çiftleri artık bir örüntü: nefes alıyor / almıyor, sıcak / soğuk, kendim / başkası. Bu çiftler karar akışlarında birleştirilmeli ya da uygulama, cevabı göstermeden önce ayırt edici bir soru sormalı ("Vücudu sıcak mı, soğuk mu?").

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
