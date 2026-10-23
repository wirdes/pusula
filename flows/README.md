# Karar akışları

Bazı durumlar birbirine çok benzer ama doğru ilk yardım tam tersidir. Örneğin tepki vermeyen biri nefes almıyorsa kalp masajı gerekir; nefes alıyorsa yan yatırılır. Arama modeli bu tür kartları birbirine karıştırabildiği için ([ölçüm sonuçları](../results/README.md)) bu kararı modele bırakmıyoruz: uygulama kullanıcıya kısa bir **soru sorar** ve cevaba göre doğru kartı gösterir.

## Nasıl çalışır

1. Kullanıcının sorusu kartlar ve akışlar arasında aranır.
2. Bulunan ilk sonuç bir akışsa ya da bir akışa bağlı kartlardan biriyse, kart doğrudan gösterilmez; akışın ilk sorusu sorulur.
3. Kullanıcının cevabı ya bir sonraki soruya, ya bir karta, ya da kısa bir mesaja (ör. "112'yi ara") götürür.

Bir kart en fazla bir akışa bağlı olabilir.

## Mevcut akışlar

| Akış | Soru | Götürdüğü kartlar |
|---|---|---|
| `bilinc-ve-nefes` | Tepki veriyor mu? Vermiyorsa: normal nefes alıyor mu? | `temel-yasam-destegi`, `bilinci-kapali-nefes-aliyor` |
| `vucut-isisi` | Cildi sıcak mı, soğuk mu? (emin değilsen: hangi ortamdaydı?) | `sicak-carpmasi`, `hipotermi` |
| `enkaz-durumu` | Enkaz altında olan sen misin? (değilse: uzvu uzun süre sıkıştı mı?) | `enkaz-altinda-kalma`, `enkazdaki-birine-yardim`, `ezilme-yaralanmasi` |

## Dosya formatı

```yaml
id: ornek-akis
title: Kısa başlık
category: ilk-yardim
priority: kritik
summary: >
  Aramada kullanılan, durumu anlatan bir iki cümle.
start: ilk-soru
nodes:
  ilk-soru:
    question: Kullanıcıya sorulacak soru?
    answers:
      - label: Birinci cevap
        card: bir-kart            # bu karta götürür
      - label: İkinci cevap
        next: ikinci-soru          # başka bir soruya götürür
      - label: Bilmiyorum
        message: 112'yi ara.       # yalnızca kısa bir mesaj gösterir
        note: İsteğe bağlı; karttan önce gösterilen kısa uyarı.
  ikinci-soru:
    question: ...
    answers: [...]
sources:
  - name: Rehberin adı
review:
  status: taslak
  reviewer: null
  date: null
```

Her cevapta `card`, `next` ya da `message` alanlarından **tam olarak biri** bulunmalıdır. Doğrulayıcı (`python scripts/validate.py`) ulaşılamayan soruları, döngüleri ve var olmayan kartları yakalar.

## Tasarım ilkeleri

- **Sorular kısa ve gözle kontrol edilebilir olmalı.** Panikteki biri tıbbi terim bilmez; "Göğsü inip kalkıyor mu?" gibi gözlenebilir şeyler sorulmalı.
- **"Emin değilim" her zaman bir seçenek olmalı** ve en güvenli yola gitmeli. Örneğin nefes konusunda emin olunamıyorsa kalp masajına başlanır.
- Güvenli bir varsayılan yoksa, cevap 112'yi aramayı ve kişiyi güvende tutmayı söyleyen bir mesaja gitmeli.
