# Bilgi kartları

Pusula'nın verdiği her cevap bu klasördeki kartlardan gelir. Model kendi başına tavsiye üretmez, yalnızca doğru kartı bulur. Bu yüzden kartların doğruluğu projenin en önemli parçasıdır.

> **Uyarı:** Şu anki kartların hepsi **taslak**. Genel ilk yardım ve afet rehberleri temel alınarak yazıldı, ancak henüz bir sağlık profesyoneli tarafından satır satır kontrol edilmedi. `review.status: onaylandi` olmayan hiçbir kart gerçek kullanıcıya gösterilmemelidir.

## Kapsam ilkesi

Pusula internetsiz çalıştığı için yalnızca **zamanla değişmeyen ve doğrulanabilir** bilgiler içerir.

- **Girer:** Nasıl yapılır bilgileri (ilk yardım, deprem, hayatta kalma, yön bulma), resmi kaynaktan doğrulanmış acil numaralar, sabit konum verileri (ör. toplanma alanları; ayrı bir veri katmanı olarak ve kaynağı ile güncelleme tarihi belirtilerek).
- **Girmez:** Sürekli değişen bilgiler: yol ve trafik durumu, nöbetçi eczaneler, toplu taşıma saatleri, hava durumu, anlık afet haberleri. İnternetsiz güncel tutulamayan bilgi yanıltıcı olur.
- **Bilerek eklenmez:** Yanlış uygulandığında ölümcül olabilecek bilgiler; örneğin hangi yabani mantar veya bitkinin yenebileceği. Bunun yerine "tanımadığını yeme" uyarısı verilir.

## Dosya düzeni

- Her kart ayrı bir YAML dosyasıdır: `cards/<id>.yaml`.
- Dosya adı kartın `id` alanıyla aynı olmalıdır.
- Kodlama UTF-8'dir; Türkçe karakterler olduğu gibi yazılır.

## Alanlar

| Alan | Zorunlu | Açıklama |
|---|---|---|
| `id` | Evet | Küçük harf, rakam ve tire (`ciddi-kanama`). Değişmez; test soruları bu kimliğe bağlanır. |
| `title` | Evet | Kısa başlık, panikteki birinin hızla tanıyacağı şekilde. |
| `category` | Evet | `deprem`, `ilk-yardim`, `tehlike`, `hayatta-kalma`, `iletisim`, `hazirlik`, `psikolojik` |
| `priority` | Evet | `kritik` (hayati, saniyeler önemli), `yuksek`, `normal` |
| `summary` | Evet | En önemli şeyi söyleyen bir iki cümle. Ekranda ilk görünen ve sesli okunan kısım. |
| `steps` | Evet | Sırayla yapılacaklar. Her madde tek bir eylem içerir. |
| `dont` | Hayır | Yapılmaması gerekenler; özellikle yaygın yanlış uygulamalar (diş macunu, kolonya koklatma vb.). |
| `seek_help` | Hayır | Hangi durumda mutlaka profesyonel yardım gerektiği. |
| `keywords` | Hayır | Günlük dilde söylenişler, eş anlamlılar, yaygın ifadeler. Aramayı güçlendirir. |
| `related` | Hayır | İlgili kartların `id` listesi. |
| `sources` | Evet | Dayanılan rehberler. Her öğe `name` ve isteğe bağlı `url` içerir. |
| `review` | Evet | `status` (`taslak`, `inceleniyor`, `onaylandi`), `reviewer`, `date`. |

## Örnek

```yaml
id: ornek-kart
title: Kartın kısa başlığı
category: ilk-yardim
priority: yuksek
summary: >
  En önemli talimat bir iki cümlede.
steps:
  - İlk yapılacak şey.
  - İkinci yapılacak şey.
dont:
  - Yaygın bir yanlış uygulama.
keywords:
  - günlük dildeki bir söyleniş
related: [baska-kart]
sources:
  - name: Rehberin adı
    url: https://ornek.org
review:
  status: taslak
  reviewer: null
  date: null
```

## YAML ipuçları

- İçinde `: ` (iki nokta ve boşluk) ya da ` #` geçen maddeleri tırnak içine alın, yoksa YAML bunları farklı yorumlar.
- Tırnakla başlayan bir madde yazacaksanız maddenin tamamını tırnağa alın.
- Yazdıktan sonra doğrulayıcıyı çalıştırın: `python scripts/validate.py`

## İnceleme süreci

1. Kart `taslak` olarak eklenir.
2. Bir sağlık profesyoneli (hekim, paramedik, ilk yardım eğitmeni) kartı kaynaklarla karşılaştırır, düzeltir ve durumu `inceleniyor` yapar.
3. Son kontrolden sonra `onaylandi`, `reviewer` ve `date` alanları doldurulur.

## Karar akışları

Birbirine benzeyen ama talimatları zıt olan kartlar (ör. kalp masajı ile yan yatırma) doğrudan aramaya bırakılmaz; [`flows/`](../flows/) klasöründeki bir karar akışına bağlanır. Arama bu kartlardan birini bulduğunda uygulama önce akışın sorusunu sorar. Yeni bir kart, mevcut bir kartla karışıp tam ters bir talimata yol açabiliyorsa onu da bir akışa bağlayın.
